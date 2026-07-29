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

"""Shared utilities for the Google Cloud KMS integration."""

import base64
import binascii
import re
import textwrap
from typing import TypeAlias

from google.api_core import exceptions as core_exceptions
from google.cloud import kms_v1
import google_crc32c
from pyasn1.codec.der import decoder as der_decoder
from pyasn1.codec.der import encoder as der_encoder
from pyasn1.error import PyAsn1Error
from pyasn1.type import univ
from pyasn1_modules import rfc5280

import tink

# Matches the resource name of a CryptoKeyVersion in Cloud KMS.
KMS_KEY_VERSION_REGEX = re.compile(
    'projects/([^/]+)/'
    'locations/([a-zA-Z0-9_-]{1,63})/'
    'keyRings/([a-zA-Z0-9_-]{1,63})/'
    'cryptoKeys/([a-zA-Z0-9_-]{1,63})/'
    'cryptoKeyVersions/([a-zA-Z0-9_-]{1,63})$'
)

_Algorithm: TypeAlias = kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm

# ML-DSA external-mu algorithms mapped to (public key OID, raw key size in
# bytes). These algorithms sign an externally computed message representative
# (mu) instead of a plain digest of the data.
ML_DSA_EXTERNAL_MU_PARAMS: dict[_Algorithm | int, tuple[str, int]] = {
    _Algorithm.PQ_SIGN_ML_DSA_44_EXTERNAL_MU: ('2.16.840.1.101.3.4.3.17', 1312),
    _Algorithm.PQ_SIGN_ML_DSA_65_EXTERNAL_MU: ('2.16.840.1.101.3.4.3.18', 1952),
    _Algorithm.PQ_SIGN_ML_DSA_87_EXTERNAL_MU: ('2.16.840.1.101.3.4.3.19', 2592),
}


def validate_kms_key_name(key_name: str) -> None:
  """Validates that key_name is a valid Cloud KMS CryptoKeyVersion name.

  MAC and Signing operations require a CryptoKeyVersion. See
  https://cloud.google.com/kms/docs/object-hierarchy.

  Args:
    key_name: The KMS key resource name to validate.

  Raises:
    tink.TinkError: If key_name is null or does not match the expected format
    for key versions.
  """
  if not key_name:
    raise tink.TinkError('key_name cannot be null.')
  if not KMS_KEY_VERSION_REGEX.match(key_name):
    raise tink.TinkError(
        f'Invalid key_name format: {key_name}. This operation requires'
        ' a CryptoKeyVersion. KMS key versions should follow the format:'
        ' "projects/<project-id>/locations/<location>/keyRings/<keyring>/'
        'cryptoKeys/<key-name>/cryptoKeyVersions/<version>"'
    )


def fetch_public_key(
    client: kms_v1.KeyManagementServiceClient, key_name: str
) -> kms_v1.PublicKey:
  """Fetches the public key for key_name from Cloud KMS and verifies integrity.

  The key is requested in PEM format, except for keys that do not support PEM
  (e.g. SLH-DSA), which are served only in NIST_PQC format.

  Args:
    client: The KMS client used to fetch the key.
    key_name: The resource name of the CryptoKeyVersion.

  Returns:
    The verified public key.

  Raises:
    tink.TinkError: If the RPC fails or the key name or checksum do not match.
  """
  try:
    response = client.get_public_key(
        request=kms_v1.GetPublicKeyRequest(
            name=key_name,
            public_key_format=kms_v1.PublicKey.PublicKeyFormat.PEM,
        )
    )
  except core_exceptions.GoogleAPIError as e:
    # Keys that do not support PEM (e.g. SLH-DSA) report this; the raw key is
    # served in NIST_PQC format instead.
    if 'Only NIST_PQC format is supported' not in str(e):
      raise tink.TinkError(e) from e
    try:
      response = client.get_public_key(
          request=kms_v1.GetPublicKeyRequest(
              name=key_name,
              public_key_format=kms_v1.PublicKey.PublicKeyFormat.NIST_PQC,
          )
      )
    except core_exceptions.GoogleAPIError as nist_error:
      raise tink.TinkError(nist_error) from nist_error
  if response.name != key_name:
    raise tink.TinkError(
        'The key name in the GetPublicKey response does not match the'
        ' requested key name.'
    )
  if response.public_key.crc32c_checksum != google_crc32c.value(
      response.public_key.data
  ):
    raise tink.TinkError('The GetPublicKey checksum does not match.')
  return response


# RFC 7468 textual-encoding boundary tokens.
_PEM_BEGIN = b'-----BEGIN '
_PEM_END = b'-----END '
_PEM_MARKER = b'-----'
_PEM_PUBLIC_KEY = b'PUBLIC KEY'


def _pem_to_der(public_key_pem: bytes) -> bytes:
  """Decodes the base64 body of a PUBLIC KEY PEM into DER bytes.

  Follows RFC 7468: content before the BEGIN boundary and after the matching
  END boundary is discarded, the encapsulated type must be a PUBLIC KEY, and
  header fields (which RFC 7468 forbids in the textual encoding) are rejected.

  Args:
    public_key_pem: The PEM-encoded public key.

  Returns:
    The DER-encoded bytes recovered from the PEM body.

  Raises:
    ValueError: If public_key_pem is not a well-formed PUBLIC KEY PEM.
  """
  lines = public_key_pem.splitlines()
  index = 0
  # Discard everything before the BEGIN boundary.
  while index < len(lines) and not lines[index].startswith(_PEM_BEGIN):
    index += 1
  if index == len(lines):
    raise ValueError("Could not find a line starting with '-----BEGIN '.")

  rest = lines[index].strip()[len(_PEM_BEGIN) :]
  marker = rest.find(_PEM_MARKER)
  if marker < 0:
    raise ValueError("Could not find the closing '-----' on the BEGIN line.")
  pem_type = rest[:marker]
  if _PEM_PUBLIC_KEY not in pem_type:
    raise ValueError('Not a PUBLIC KEY PEM.')

  end_marker = _PEM_END + pem_type + _PEM_MARKER
  contents = []
  for line in lines[index + 1 :]:
    if end_marker in line:
      # Any content after the matching END boundary is discarded.
      try:
        return base64.b64decode(b''.join(contents), validate=True)
      except binascii.Error as e:
        raise ValueError('Invalid base64 encoding in PEM.') from e
    # RFC 7468 forbids header fields in the textual encoding.
    if b':' in line:
      raise ValueError('Found a header field in the PEM.')
    contents.append(line.strip())
  raise ValueError("Could not find the matching '-----END ' boundary.")


def parse_spki_pem(public_key_pem: bytes) -> rfc5280.SubjectPublicKeyInfo:
  """Decodes the PEM-encoded SubjectPublicKeyInfo returned by Cloud KMS.

  Args:
    public_key_pem: The PEM-encoded public key.

  Returns:
    The decoded SubjectPublicKeyInfo.

  Raises:
    tink.TinkError: If the PEM cannot be parsed.
  """
  try:
    der = _pem_to_der(public_key_pem)
    decoded = der_decoder.decode(der, asn1Spec=rfc5280.SubjectPublicKeyInfo())
    if not decoded or len(decoded) != 2:
      raise ValueError(f'Unexpected decode result: {decoded}')
    spki, _ = decoded
  except (PyAsn1Error, ValueError) as e:
    raise tink.TinkError('Failed to parse the public key PEM.') from e
  return spki


def extract_raw_ml_dsa_public_key(
    public_key_pem: bytes, expected_oid: str, expected_size: int
) -> bytes:
  """Recovers the raw ML-DSA public key from a PEM-encoded SubjectPublicKeyInfo.

  The raw key (rho || t1) is the subjectPublicKey of the SubjectPublicKeyInfo.
  Its algorithm OID and length are checked against the expected values before it
  is returned.

  Args:
    public_key_pem: The PEM-encoded ML-DSA public key returned by Cloud KMS.
    expected_oid: The algorithm OID the public key is expected to carry.
    expected_size: The expected length of the raw public key in bytes.

  Returns:
    The raw ML-DSA public key (rho || t1).

  Raises:
    tink.TinkError: If the PEM cannot be parsed, or the OID or key length do not
      match the expected values.
  """
  try:
    spki = parse_spki_pem(public_key_pem)
    oid = str(spki['algorithm']['algorithm'])
    raw_public_key = spki['subjectPublicKey'].asOctets()
  except (PyAsn1Error, ValueError, tink.TinkError) as e:
    raise tink.TinkError('Failed to parse the ML-DSA public key.') from e
  if oid != expected_oid:
    raise tink.TinkError(f'Unexpected public key OID {oid}.')
  if len(raw_public_key) != expected_size:
    raise tink.TinkError(
        f'Incorrect public key size: got {len(raw_public_key)} bytes, want'
        f' {expected_size}.'
    )
  return raw_public_key


def raw_ml_dsa_public_key_to_pem(oid: str, raw_public_key: bytes) -> bytes:
  """Builds a PEM-encoded SubjectPublicKeyInfo for an ML-DSA public key."""
  spki = rfc5280.SubjectPublicKeyInfo()
  spki['algorithm']['algorithm'] = univ.ObjectIdentifier(oid)
  spki['subjectPublicKey'] = univ.BitString(hexValue=raw_public_key.hex())
  der = der_encoder.encode(spki)
  body = base64.b64encode(der).decode()
  wrapped_body = '\n'.join(textwrap.wrap(body, width=64))
  return (
      f'-----BEGIN PUBLIC KEY-----\n{wrapped_body}\n-----END PUBLIC KEY-----'
  ).encode()
