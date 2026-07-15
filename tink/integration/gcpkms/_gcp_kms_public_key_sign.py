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

"""A PublicKeySign primitive backed by Google Cloud KMS."""

import hashlib
from typing import TypeAlias

from google.api_core import exceptions as core_exceptions
from google.cloud import kms_v1
import google_crc32c

import tink
from tink import signature
from tink.integration.gcpkms import _gcp_kms_util

# Maximum size of the data that can be signed.
_MAX_SIGN_DATA_SIZE = 64 * 1024

_Algorithm: TypeAlias = kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm

# Digest-based signing algorithms mapped to the hash used to compute the digest.
# The hashlib name (e.g. "sha256") is also the kms_v1.Digest oneof field name,
# so this single mapping drives both digest computation and request building.
_DIGEST_ALGORITHM_TO_HASH = {
    _Algorithm.EC_SIGN_P256_SHA256: 'sha256',
    _Algorithm.EC_SIGN_SECP256K1_SHA256: 'sha256',
    _Algorithm.RSA_SIGN_PSS_2048_SHA256: 'sha256',
    _Algorithm.RSA_SIGN_PSS_3072_SHA256: 'sha256',
    _Algorithm.RSA_SIGN_PSS_4096_SHA256: 'sha256',
    _Algorithm.RSA_SIGN_PKCS1_2048_SHA256: 'sha256',
    _Algorithm.RSA_SIGN_PKCS1_3072_SHA256: 'sha256',
    _Algorithm.RSA_SIGN_PKCS1_4096_SHA256: 'sha256',
    _Algorithm.EC_SIGN_P384_SHA384: 'sha384',
    _Algorithm.RSA_SIGN_PSS_4096_SHA512: 'sha512',
    _Algorithm.RSA_SIGN_PKCS1_4096_SHA512: 'sha512',
}

# Algorithms that sign the raw data instead of a digest.
_DATA_BASED_ALGORITHMS = frozenset({
    _Algorithm.EC_SIGN_ED25519,
    _Algorithm.RSA_SIGN_RAW_PKCS1_2048,
    _Algorithm.RSA_SIGN_RAW_PKCS1_3072,
    _Algorithm.RSA_SIGN_RAW_PKCS1_4096,
})

# KMS algorithms supported for signing.
_SUPPORTED_ALGORITHMS = (
    frozenset(_DIGEST_ALGORITHM_TO_HASH) | _DATA_BASED_ALGORITHMS
)


class _GcpKmsPublicKeySign(signature.PublicKeySign):
  """Implements the PublicKeySign interface for GCP KMS.

  Signing is forwarded to a CryptoKeyVersion in Google Cloud KMS via the
  AsymmetricSign RPC. The integrity of each request and response is protected
  with CRC32C checksums.
  """

  def __init__(
      self, client: kms_v1.KeyManagementServiceClient, key_name: str
  ) -> None:
    _gcp_kms_util.validate_kms_key_name(key_name)
    if not client:
      raise tink.TinkError('client cannot be null.')
    self._client = client
    self._name = key_name
    self._public_key = self._fetch_public_key()
    if self._public_key.algorithm not in _SUPPORTED_ALGORITHMS:
      raise tink.TinkError(
          f'The algorithm {self._public_key.algorithm.name} is not supported.'
      )

  def _fetch_public_key(self) -> kms_v1.PublicKey:
    """Fetches the public key from KMS and verifies its integrity."""
    try:
      response = self._client.get_public_key(
          request=kms_v1.GetPublicKeyRequest(
              name=self._name,
              public_key_format=kms_v1.PublicKey.PublicKeyFormat.PEM,
          )
      )
    except core_exceptions.GoogleAPIError as e:
      raise tink.TinkError(e) from e
    if response.name != self._name:
      raise tink.TinkError(
          'The key name in the GetPublicKey response does not match the'
          ' requested key name.'
      )
    if response.public_key.crc32c_checksum != google_crc32c.value(
        response.public_key.data
    ):
      raise tink.TinkError('The GetPublicKey checksum does not match.')
    return response

  def _requires_data_for_sign(self) -> bool:
    """Returns whether signing operates on the raw data rather than a digest."""
    if self._public_key.algorithm in _DATA_BASED_ALGORITHMS:
      return True
    return self._public_key.protection_level in (
        kms_v1.ProtectionLevel.EXTERNAL,
        kms_v1.ProtectionLevel.EXTERNAL_VPC,
    )

  def _build_asymmetric_sign_request(
      self, data: bytes
  ) -> kms_v1.AsymmetricSignRequest:
    """Builds the AsymmetricSign request for the configured algorithm.

    Args:
      data: The data to be signed.

    Returns:
      The AsymmetricSignRequest.

    Raises:
      tink.TinkError: If the public key algorithm is not supported, or if the
        data size is larger than the allowed size when signing raw data.
    """
    if self._requires_data_for_sign():
      if len(data) > _MAX_SIGN_DATA_SIZE:
        raise tink.TinkError(
            'The data size is larger than the allowed size:'
            f' {_MAX_SIGN_DATA_SIZE}.'
        )
      return kms_v1.AsymmetricSignRequest(
          name=self._name,
          data=data,
          data_crc32c=google_crc32c.value(data),
      )
    hash_name = _DIGEST_ALGORITHM_TO_HASH.get(self._public_key.algorithm)
    if hash_name is None:
      raise tink.TinkError(
          f'The algorithm {self._public_key.algorithm.name} does not support'
          ' digests.'
      )
    digest = hashlib.new(hash_name, data).digest()
    return kms_v1.AsymmetricSignRequest(
        name=self._name,
        digest=kms_v1.Digest(**{hash_name: digest}),
        digest_crc32c=google_crc32c.value(digest),
    )

  def _verify_sign_response(
      self, response: kms_v1.AsymmetricSignResponse
  ) -> None:
    """Verifies the integrity of an AsymmetricSign response.

    Args:
      response: The response returned by the KMS AsymmetricSign RPC.

    Raises:
      tink.TinkError: If key names or CRC32C checksums fail verification.
    """
    if response.name != self._name:
      raise tink.TinkError(
          'The key name in the response does not match the requested key name.'
      )
    # Since we request either data or digest signing, exactly one of the input
    # checksum fields is expected to be verified.
    if (
        not response.verified_data_crc32c
        and not response.verified_digest_crc32c
    ):
      raise tink.TinkError('Checking the input checksum failed.')
    if response.signature_crc32c != google_crc32c.value(response.signature):
      raise tink.TinkError('Signature checksum mismatch.')

  def sign(self, data: bytes) -> bytes:
    request = self._build_asymmetric_sign_request(data)
    try:
      response = self._client.asymmetric_sign(request=request)
    except core_exceptions.GoogleAPIError as e:
      raise tink.TinkError(e) from e
    self._verify_sign_response(response)
    return response.signature


def new_gcp_kms_public_key_sign(
    key_name: str, kms_client: kms_v1.KeyManagementServiceClient
) -> signature.PublicKeySign:
  """Creates a PublicKeySign primitive backed by Google Cloud KMS.

  Args:
    key_name: The resource name of a CryptoKeyVersion in Cloud KMS, of the form
      "projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*" (see
      https://cloud.google.com/kms/docs/object-hierarchy).
    kms_client: A google.cloud.kms_v1.KeyManagementServiceClient used to
      communicate with Cloud KMS.

  Returns:
    A PublicKeySign object.

  Raises:
    TinkError: If key_name is not a valid CryptoKeyVersion name, kms_client is
      None, or the key's algorithm is not supported.
  """
  return _GcpKmsPublicKeySign(kms_client, key_name)
