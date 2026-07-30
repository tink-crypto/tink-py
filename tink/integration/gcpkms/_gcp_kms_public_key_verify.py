# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A PublicKeyVerify primitive backed by Google Cloud KMS."""

from typing import TypeAlias

from google.cloud import kms_v1
from pyasn1.codec.der import decoder as der_decoder
from pyasn1.error import PyAsn1Error
from pyasn1_modules import rfc3447

from tink.proto import common_pb2
from tink.proto import ecdsa_pb2
from tink.proto import ml_dsa_pb2
from tink.proto import rsa_ssa_pkcs1_pb2
from tink.proto import rsa_ssa_pss_pb2
from tink.proto import slh_dsa_pb2
from tink.proto import tink_pb2
import tink
from tink import signature as tink_signature
from tink.integration.gcpkms import _gcp_kms_util
from tink.internal import big_integer_util

_Algorithm: TypeAlias = kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm

# Type URLs of the Tink public key protos used to build the local verifier.
_ECDSA_TYPE_URL = 'type.googleapis.com/google.crypto.tink.EcdsaPublicKey'
_RSA_SSA_PKCS1_TYPE_URL = (
    'type.googleapis.com/google.crypto.tink.RsaSsaPkcs1PublicKey'
)
_RSA_SSA_PSS_TYPE_URL = (
    'type.googleapis.com/google.crypto.tink.RsaSsaPssPublicKey'
)
_ML_DSA_TYPE_URL = 'type.googleapis.com/google.crypto.tink.MlDsaPublicKey'
_SLH_DSA_TYPE_URL = 'type.googleapis.com/google.crypto.tink.SlhDsaPublicKey'

# ECDSA algorithms mapped to (curve, hash, coordinate length in bytes). KMS
# emits DER-encoded ECDSA signatures.
_ECDSA_PARAMS: dict[
    _Algorithm | int,
    tuple[common_pb2.EllipticCurveType, common_pb2.HashType, int],
] = {
    _Algorithm.EC_SIGN_P256_SHA256: (
        common_pb2.NIST_P256,
        common_pb2.SHA256,
        32,
    ),
    _Algorithm.EC_SIGN_P384_SHA384: (
        common_pb2.NIST_P384,
        common_pb2.SHA384,
        48,
    ),
}

# RSA SSA PKCS1 algorithms mapped to the signature hash.
_RSA_PKCS1_PARAMS: dict[_Algorithm | int, common_pb2.HashType] = {
    _Algorithm.RSA_SIGN_PKCS1_2048_SHA256: common_pb2.SHA256,
    _Algorithm.RSA_SIGN_PKCS1_3072_SHA256: common_pb2.SHA256,
    _Algorithm.RSA_SIGN_PKCS1_4096_SHA256: common_pb2.SHA256,
    _Algorithm.RSA_SIGN_PKCS1_4096_SHA512: common_pb2.SHA512,
}

# RSA SSA PSS algorithms mapped to (hash, salt length in bytes). KMS uses the
# signature hash for MGF1 and a salt length equal to the hash length.
_RSA_PSS_PARAMS: dict[_Algorithm | int, tuple[common_pb2.HashType, int]] = {
    _Algorithm.RSA_SIGN_PSS_2048_SHA256: (common_pb2.SHA256, 32),
    _Algorithm.RSA_SIGN_PSS_3072_SHA256: (common_pb2.SHA256, 32),
    _Algorithm.RSA_SIGN_PSS_4096_SHA256: (common_pb2.SHA256, 32),
    _Algorithm.RSA_SIGN_PSS_4096_SHA512: (common_pb2.SHA512, 64),
}

# ML-DSA algorithms mapped to (Tink instance, public key OID, raw key size in
# bytes). Cloud KMS serves these in PEM format; the raw key (rho || t1) is the
# subjectPublicKey. The external-mu algorithms map to the same ML-DSA instances,
# since an external-mu signature over a message is byte-identical to a plain
# ML-DSA signature over it.
_ML_DSA_PARAMS: dict[
    _Algorithm | int, tuple[ml_dsa_pb2.MlDsaInstance, str, int]
] = {
    _Algorithm.PQ_SIGN_ML_DSA_44: (
        ml_dsa_pb2.ML_DSA_44,
        '2.16.840.1.101.3.4.3.17',
        1312,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_44_EXTERNAL_MU: (
        ml_dsa_pb2.ML_DSA_44,
        '2.16.840.1.101.3.4.3.17',
        1312,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_65: (
        ml_dsa_pb2.ML_DSA_65,
        '2.16.840.1.101.3.4.3.18',
        1952,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_65_EXTERNAL_MU: (
        ml_dsa_pb2.ML_DSA_65,
        '2.16.840.1.101.3.4.3.18',
        1952,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_87: (
        ml_dsa_pb2.ML_DSA_87,
        '2.16.840.1.101.3.4.3.19',
        2592,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_87_EXTERNAL_MU: (
        ml_dsa_pb2.ML_DSA_87,
        '2.16.840.1.101.3.4.3.19',
        2592,
    ),
}

# Private key size in bytes for SLH-DSA-SHA2-128s
_SLH_DSA_PRIVATE_KEY_SIZE = 64

# Fixed key ID for the single-key keyset. KMS produces raw signatures with no
# Tink output prefix, so the key ID does not appear in the signature.
_KEY_ID = 1


def _ecdsa_public_key(public_key_pem: bytes, algorithm: _Algorithm) -> bytes:
  """Builds a serialized EcdsaPublicKey proto from a PEM public key.

  Args:
    public_key_pem: The PEM-encoded ECDSA public key returned by Cloud KMS.
    algorithm: The CryptoKeyVersion algorithm of the public key.

  Returns:
    The serialized EcdsaPublicKey proto bytes.

  Raises:
    tink.TinkError: If the PEM cannot be parsed or has an invalid format.
  """
  curve, hash_type, coordinate_size = _ECDSA_PARAMS[algorithm]
  spki = _gcp_kms_util.parse_spki_pem(public_key_pem)
  # The subjectPublicKey is the uncompressed point 0x04 || x || y.
  point = spki['subjectPublicKey'].asOctets()
  if len(point) != 2 * coordinate_size + 1 or point[0] != 0x04:
    raise tink.TinkError(
        f'Unexpected ECDSA public key point for {algorithm.name}.'
    )
  public_key = ecdsa_pb2.EcdsaPublicKey(
      version=0,
      params=ecdsa_pb2.EcdsaParams(
          hash_type=hash_type, curve=curve, encoding=ecdsa_pb2.DER
      ),
      x=point[1 : 1 + coordinate_size],
      y=point[1 + coordinate_size :],
  )
  return public_key.SerializeToString()


def _rsa_modulus_and_exponent(public_key_pem: bytes) -> tuple[bytes, bytes]:
  """Extracts the modulus and public exponent from an RSA PEM public key.

  Args:
    public_key_pem: The PEM-encoded RSA public key returned by Cloud KMS.

  Returns:
    A tuple of (modulus, exponent) encoded as big-endian bytes.

  Raises:
    tink.TinkError: If the PEM cannot be parsed or is not a valid RSA key.
  """
  spki = _gcp_kms_util.parse_spki_pem(public_key_pem)
  try:
    # The subjectPublicKey is a DER RSAPublicKey (RFC 3447):
    # SEQUENCE { modulus INTEGER, publicExponent INTEGER }.
    decoded = der_decoder.decode(
        spki['subjectPublicKey'].asOctets(), asn1Spec=rfc3447.RSAPublicKey()
    )
    if not decoded or len(decoded) != 2:
      raise ValueError(f'Unexpected decode result: {decoded}')
    rsa_public_key, _ = decoded
    modulus = int(rsa_public_key['modulus'])
    exponent = int(rsa_public_key['publicExponent'])
  except (PyAsn1Error, ValueError) as e:
    raise tink.TinkError('Failed to parse the RSA public key.') from e
  return (
      big_integer_util.num_to_bytes(modulus),
      big_integer_util.num_to_bytes(exponent),
  )


def _rsa_ssa_pkcs1_public_key(
    public_key_pem: bytes, algorithm: _Algorithm
) -> bytes:
  """Builds a serialized RsaSsaPkcs1PublicKey proto from a PEM public key.

  Args:
    public_key_pem: The PEM-encoded RSA public key returned by Cloud KMS.
    algorithm: The CryptoKeyVersion algorithm of the public key.

  Returns:
    The serialized RsaSsaPkcs1PublicKey proto bytes.

  Raises:
    tink.TinkError: If the PEM cannot be parsed or is not a valid RSA key.
  """
  hash_type = _RSA_PKCS1_PARAMS[algorithm]
  modulus, exponent = _rsa_modulus_and_exponent(public_key_pem)
  public_key = rsa_ssa_pkcs1_pb2.RsaSsaPkcs1PublicKey(
      version=0,
      params=rsa_ssa_pkcs1_pb2.RsaSsaPkcs1Params(hash_type=hash_type),
      n=modulus,
      e=exponent,
  )
  return public_key.SerializeToString()


def _rsa_ssa_pss_public_key(
    public_key_pem: bytes, algorithm: _Algorithm
) -> bytes:
  """Builds a serialized RsaSsaPssPublicKey proto from a PEM public key.

  Args:
    public_key_pem: The PEM-encoded RSA public key returned by Cloud KMS.
    algorithm: The CryptoKeyVersion algorithm of the public key.

  Returns:
    The serialized RsaSsaPssPublicKey proto bytes.

  Raises:
    tink.TinkError: If the PEM cannot be parsed or is not a valid RSA key.
  """
  hash_type, salt_length = _RSA_PSS_PARAMS[algorithm]
  modulus, exponent = _rsa_modulus_and_exponent(public_key_pem)
  public_key = rsa_ssa_pss_pb2.RsaSsaPssPublicKey(
      version=0,
      params=rsa_ssa_pss_pb2.RsaSsaPssParams(
          sig_hash=hash_type, mgf1_hash=hash_type, salt_length=salt_length
      ),
      n=modulus,
      e=exponent,
  )
  return public_key.SerializeToString()


def _ml_dsa_public_key(public_key_pem: bytes, algorithm: _Algorithm) -> bytes:
  """Builds a serialized MlDsaPublicKey proto from a PEM public key.

  Args:
    public_key_pem: The PEM-encoded ML-DSA public key returned by Cloud KMS.
    algorithm: The CryptoKeyVersion algorithm of the public key.

  Returns:
    The serialized MlDsaPublicKey proto bytes.

  Raises:
    tink.TinkError: If the PEM cannot be parsed or has an unexpected OID or
      size.
  """
  instance, oid, size = _ML_DSA_PARAMS[algorithm]
  raw_public_key = _gcp_kms_util.extract_raw_ml_dsa_public_key(
      public_key_pem, oid, size
  )
  public_key = ml_dsa_pb2.MlDsaPublicKey(
      version=0,
      key_value=raw_public_key,
      params=ml_dsa_pb2.MlDsaParams(ml_dsa_instance=instance),
  )
  return public_key.SerializeToString()


def _slh_dsa_public_key(raw_public_key: bytes) -> bytes:
  """Builds a serialized SlhDsaPublicKey proto from a raw public key.

  Unlike the other algorithms, Cloud KMS serves SLH-DSA only in NIST_PQC format,
  so the input is the raw public key rather than a PEM. Its length is validated
  by the key manager when the verifier is built.

  Args:
    raw_public_key: The raw SLH-DSA public key bytes from Cloud KMS.

  Returns:
    The serialized SlhDsaPublicKey proto bytes.
  """
  public_key = slh_dsa_pb2.SlhDsaPublicKey(
      version=0,
      key_value=raw_public_key,
      params=slh_dsa_pb2.SlhDsaParams(
          key_size=_SLH_DSA_PRIVATE_KEY_SIZE,
          hash_type=slh_dsa_pb2.SHA2,
          sig_type=slh_dsa_pb2.SMALL_SIGNATURE,
      ),
  )
  return public_key.SerializeToString()


def _verifier_from_key_data(
    type_url: str, value: bytes
) -> tink_signature.PublicKeyVerify:
  """Wraps a single public key in a keyset and returns a local verifier.

  KMS produces raw signatures without a Tink output prefix, so the key uses the
  RAW output prefix type.

  Args:
    type_url: The type URL of the public key proto.
    value: The serialized public key proto.

  Returns:
    A PublicKeyVerify primitive for the public key.
  """
  tink_signature.register()
  keyset = tink_pb2.Keyset(
      primary_key_id=_KEY_ID,
      key=[
          tink_pb2.Keyset.Key(
              key_data=tink_pb2.KeyData(
                  type_url=type_url,
                  value=value,
                  key_material_type=tink_pb2.KeyData.ASYMMETRIC_PUBLIC,
              ),
              status=tink_pb2.ENABLED,
              key_id=_KEY_ID,
              output_prefix_type=tink_pb2.RAW,
          )
      ],
  )
  handle = tink.proto_keyset_format.parse_without_secret(
      keyset.SerializeToString()
  )
  return handle.primitive(tink_signature.PublicKeyVerify)


def _internal_verifier(
    algorithm: _Algorithm, public_key_data: bytes
) -> tink_signature.PublicKeyVerify:
  """Builds a local verifier for the given KMS algorithm and public key.

  The algorithm mapping also acts as the support check: unsupported algorithms
  fail here.

  Args:
    algorithm: The CryptoKeyVersion algorithm of the public key.
    public_key_data: The public key as returned by Cloud KMS.

  Returns:
    A PublicKeyVerify primitive for the public key.

  Raises:
    tink.TinkError: If the algorithm is not supported or the key cannot be
      parsed.
  """
  if algorithm in _ECDSA_PARAMS:
    value = _ecdsa_public_key(public_key_data, algorithm)
    type_url = _ECDSA_TYPE_URL
  elif algorithm in _RSA_PKCS1_PARAMS:
    value = _rsa_ssa_pkcs1_public_key(public_key_data, algorithm)
    type_url = _RSA_SSA_PKCS1_TYPE_URL
  elif algorithm in _RSA_PSS_PARAMS:
    value = _rsa_ssa_pss_public_key(public_key_data, algorithm)
    type_url = _RSA_SSA_PSS_TYPE_URL
  elif algorithm in _ML_DSA_PARAMS:
    value = _ml_dsa_public_key(public_key_data, algorithm)
    type_url = _ML_DSA_TYPE_URL
  elif algorithm == _Algorithm.PQ_SIGN_SLH_DSA_SHA2_128S:
    value = _slh_dsa_public_key(public_key_data)
    type_url = _SLH_DSA_TYPE_URL
  else:
    raise tink.TinkError(f'The algorithm {algorithm.name} is not supported.')
  return _verifier_from_key_data(type_url, value)


class _GcpKmsPublicKeyVerify(tink_signature.PublicKeyVerify):
  """Implements the PublicKeyVerify interface for GCP KMS.

  Cloud KMS does not offer a verification RPC. The public key is fetched (or
  supplied) once, when the verifier is built, and signatures are then verified
  locally with Tink; Cloud KMS is not contacted again.
  """

  def __init__(self, verifier: tink_signature.PublicKeyVerify) -> None:
    """Initializes the verification instance."""
    self._verifier = verifier

  def verify(self, signature: bytes, data: bytes) -> None:  # pytype: disable=signature-mismatch
    """See base class."""
    self._verifier.verify(signature, data)


def new_gcp_kms_public_key_verify(
    key_name: str, kms_client: kms_v1.KeyManagementServiceClient
) -> tink_signature.PublicKeyVerify:
  """Creates a PublicKeyVerify primitive backed by Google Cloud KMS.

  The public key is fetched from Cloud KMS, its integrity is verified, and a
  local verifier is built. No Cloud KMS calls are made when verifying.

  Args:
    key_name: The resource name of a CryptoKeyVersion in Cloud KMS, of the form
      "projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*" (see
      https://cloud.google.com/kms/docs/object-hierarchy).
    kms_client: A google.cloud.kms_v1.KeyManagementServiceClient used to
      communicate with Cloud KMS.

  Returns:
    A PublicKeyVerify object.

  Raises:
    tink.TinkError: If key_name is not a valid CryptoKeyVersion name, kms_client
      is None, or the key's algorithm is not supported.
  """
  _gcp_kms_util.validate_kms_key_name(key_name)
  if not kms_client:
    raise tink.TinkError('kms_client cannot be null.')
  public_key = _gcp_kms_util.fetch_public_key(kms_client, key_name)
  return _GcpKmsPublicKeyVerify(
      _internal_verifier(public_key.algorithm, public_key.public_key.data)
  )


def new_gcp_kms_public_key_verify_no_rpc(
    public_key: bytes, algorithm: _Algorithm
) -> tink_signature.PublicKeyVerify:
  """Creates a PublicKeyVerify primitive from a pre-fetched public key.

  No Cloud KMS calls are made. Unlike new_gcp_kms_public_key_verify, this path
  cannot verify the KMS response checksum or key name, so the caller is
  responsible for the integrity and provenance of the public key material.

  Args:
    public_key: The public key previously returned by Cloud KMS GetPublicKey for
      the algorithm. This is the PEM-encoded key for classical and ML-DSA
      algorithms, and the raw NIST_PQC key for SLH-DSA.
    algorithm: The CryptoKeyVersion algorithm of the public key.

  Returns:
    A PublicKeyVerify object.

  Raises:
    tink.TinkError: If public_key is empty or the algorithm is not supported.
  """
  if not public_key:
    raise tink.TinkError('public_key cannot be empty.')
  return _GcpKmsPublicKeyVerify(_internal_verifier(algorithm, public_key))
