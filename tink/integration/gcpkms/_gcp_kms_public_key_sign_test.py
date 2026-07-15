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

import hashlib
from typing import TypeAlias
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.api_core import exceptions as core_exceptions
from google.cloud import kms_v1
import google_crc32c

from tink import core
from tink.integration.gcpkms import _gcp_kms_public_key_sign


_KEY_VERSION = 'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1'
_OTHER_KEY_VERSION = 'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/2'
_DATA = b'data to sign'
_SIGNATURE = b'signature for data to sign'
_PUBLIC_KEY_DATA = (
    b'-----BEGIN PUBLIC KEY-----\nfake pem\n-----END PUBLIC KEY-----'
)

_Algorithm: TypeAlias = kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm


def _public_key_response(
    name: str = _KEY_VERSION,
    algorithm: kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm = _Algorithm.EC_SIGN_P256_SHA256,
    protection_level: kms_v1.ProtectionLevel = kms_v1.ProtectionLevel.SOFTWARE,
    data: bytes = _PUBLIC_KEY_DATA,
    crc32c_checksum: int | None = None,
) -> kms_v1.types.PublicKey:
  if crc32c_checksum is None:
    crc32c_checksum = google_crc32c.value(data)
  return kms_v1.types.PublicKey(
      name=name,
      algorithm=algorithm,
      protection_level=protection_level,
      public_key=kms_v1.types.ChecksummedData(
          data=data, crc32c_checksum=crc32c_checksum
      ),
  )


def _sign_response(
    name: str = _KEY_VERSION,
    signature: bytes = _SIGNATURE,
    verified_data_crc32c: bool = False,
    verified_digest_crc32c: bool = True,
    signature_crc32c: int | None = None,
) -> kms_v1.types.AsymmetricSignResponse:
  if signature_crc32c is None:
    signature_crc32c = google_crc32c.value(signature)
  return kms_v1.types.AsymmetricSignResponse(
      name=name,
      signature=signature,
      verified_data_crc32c=verified_data_crc32c,
      verified_digest_crc32c=verified_digest_crc32c,
      signature_crc32c=signature_crc32c,
  )


class CustomException(core_exceptions.GoogleAPIError):
  pass


class GcpKmsPublicKeySignTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    mock.patch.object(kms_v1, 'KeyManagementServiceClient').start()
    kms_v1.KeyManagementServiceClient().get_public_key.return_value = (
        _public_key_response()
    )

  def tearDown(self):
    mock.patch.stopall()
    super().tearDown()

  def _new_signer(
      self,
      algorithm: kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm = _Algorithm.EC_SIGN_P256_SHA256,
      protection_level: kms_v1.ProtectionLevel = kms_v1.ProtectionLevel.SOFTWARE,
  ) -> _gcp_kms_public_key_sign._GcpKmsPublicKeySign:
    """Builds a signer for the given algorithm and protection level."""
    kms_v1.KeyManagementServiceClient().get_public_key.return_value = (
        _public_key_response(
            algorithm=algorithm, protection_level=protection_level
        )
    )
    return _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign(
        _KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )

  def test_client_null(self):
    with self.assertRaisesRegex(core.TinkError, r'client cannot be null'):
      _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign(_KEY_VERSION, None)

  @parameterized.parameters(
      '',
      None,
      'wrong/kms/key/format',
      # A CryptoKey is not enough; signing requires a CryptoKeyVersion.
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1',
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions',
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1/',
      'gcp-kms://projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1',
  )
  def test_key_name_format_wrong(self, key_name):
    with self.assertRaisesRegex(
        core.TinkError, r'key_name cannot be null|Invalid key_name format'
    ):
      _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign(
          key_name, kms_v1.KeyManagementServiceClient()
      )

  def test_construction_unsupported_algorithm_fails(self):
    kms_v1.KeyManagementServiceClient().get_public_key.return_value = (
        _public_key_response(algorithm=_Algorithm.GOOGLE_SYMMETRIC_ENCRYPTION)
    )
    with self.assertRaisesRegex(core.TinkError, r'is not supported'):
      _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign(
          _KEY_VERSION, kms_v1.KeyManagementServiceClient()
      )

  def test_get_public_key_rpc_fails(self):
    kms_v1.KeyManagementServiceClient().get_public_key.side_effect = (
        CustomException()
    )
    with self.assertRaises(core.TinkError):
      _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign(
          _KEY_VERSION, kms_v1.KeyManagementServiceClient()
      )

  def test_get_public_key_response_key_name_mismatch_fails(self):
    kms_v1.KeyManagementServiceClient().get_public_key.return_value = (
        _public_key_response(name=_OTHER_KEY_VERSION)
    )
    with self.assertRaisesRegex(
        core.TinkError,
        r'The key name in the GetPublicKey response does not match',
    ):
      _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign(
          _KEY_VERSION, kms_v1.KeyManagementServiceClient()
      )

  def test_get_public_key_checksum_mismatch_fails(self):
    kms_v1.KeyManagementServiceClient().get_public_key.return_value = (
        _public_key_response(crc32c_checksum=1)
    )
    with self.assertRaisesRegex(
        core.TinkError, r'The GetPublicKey checksum does not match'
    ):
      _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign(
          _KEY_VERSION, kms_v1.KeyManagementServiceClient()
      )

  def test_construction_succeeds_for_supported_algorithm(self):
    self.assertIsNotNone(self._new_signer())

  @parameterized.parameters(*_gcp_kms_public_key_sign._DATA_BASED_ALGORITHMS)
  def test_sign_data_too_large_fails(self, algorithm):
    signer = self._new_signer(algorithm=algorithm)
    with self.assertRaisesRegex(
        core.TinkError, r'The data size is larger than the allowed size'
    ):
      signer.sign(b'a' * (_gcp_kms_public_key_sign._MAX_SIGN_DATA_SIZE + 1))

  def test_sign_large_data_succeeds_for_digest_based_algorithm(self):
    kms_v1.KeyManagementServiceClient().asymmetric_sign.return_value = (
        _sign_response()
    )
    signer = self._new_signer(algorithm=_Algorithm.EC_SIGN_P256_SHA256)
    large_data = b'a' * (_gcp_kms_public_key_sign._MAX_SIGN_DATA_SIZE + 1)
    self.assertEqual(signer.sign(large_data), _SIGNATURE)

  def test_sign_rpc_fails(self):
    kms_v1.KeyManagementServiceClient().asymmetric_sign.side_effect = (
        CustomException()
    )
    signer = self._new_signer()
    with self.assertRaises(core.TinkError):
      signer.sign(_DATA)

  def test_verify_sign_response_success(self):
    signer = self._new_signer()
    self.assertIsNone(signer._verify_sign_response(_sign_response()))

  def test_verify_sign_response_key_name_mismatch_fails(self):
    signer = self._new_signer()
    with self.assertRaisesRegex(
        core.TinkError, r'The key name in the response does not match'
    ):
      signer._verify_sign_response(_sign_response(name=_OTHER_KEY_VERSION))

  def test_verify_sign_response_no_checksum_verified_fails(self):
    signer = self._new_signer()
    with self.assertRaisesRegex(
        core.TinkError, r'Checking the input checksum failed'
    ):
      signer._verify_sign_response(
          _sign_response(
              verified_data_crc32c=False, verified_digest_crc32c=False
          )
      )

  def test_verify_sign_response_signature_crc32c_mismatch_fails(self):
    signer = self._new_signer()
    with self.assertRaisesRegex(core.TinkError, r'Signature checksum mismatch'):
      signer._verify_sign_response(_sign_response(signature_crc32c=1))

  @parameterized.parameters(
      *_gcp_kms_public_key_sign._DIGEST_ALGORITHM_TO_HASH.items()
  )
  def test_sign_digest_based_algorithm(self, algorithm, hash_name):
    client = kms_v1.KeyManagementServiceClient()
    client.asymmetric_sign.return_value = _sign_response()
    signer = self._new_signer(algorithm=algorithm)

    self.assertEqual(signer.sign(_DATA), _SIGNATURE)

    request = client.asymmetric_sign.call_args.kwargs['request']
    expected_digest = hashlib.new(hash_name, _DATA).digest()
    self.assertEqual(request.name, _KEY_VERSION)
    self.assertEqual(getattr(request.digest, hash_name), expected_digest)
    self.assertEqual(
        request.digest_crc32c, google_crc32c.value(expected_digest)
    )
    self.assertEqual(request.data, b'')

  @parameterized.parameters(*_gcp_kms_public_key_sign._DATA_BASED_ALGORITHMS)
  def test_sign_data_based_algorithm(self, algorithm):
    client = kms_v1.KeyManagementServiceClient()
    client.asymmetric_sign.return_value = _sign_response(
        verified_data_crc32c=True, verified_digest_crc32c=False
    )
    signer = self._new_signer(algorithm=algorithm)

    self.assertEqual(signer.sign(_DATA), _SIGNATURE)

    request = client.asymmetric_sign.call_args.kwargs['request']
    self.assertEqual(request.name, _KEY_VERSION)
    self.assertEqual(request.data, _DATA)
    self.assertEqual(request.data_crc32c, google_crc32c.value(_DATA))
    # No digest is set for data-based signing.
    self.assertEqual(request.digest.sha256, b'')
    self.assertEqual(request.digest.sha384, b'')
    self.assertEqual(request.digest.sha512, b'')

  @parameterized.parameters(
      kms_v1.ProtectionLevel.EXTERNAL,
      kms_v1.ProtectionLevel.EXTERNAL_VPC,
  )
  def test_sign_external_protection_uses_data_path(self, protection_level):
    client = kms_v1.KeyManagementServiceClient()
    client.asymmetric_sign.return_value = _sign_response(
        verified_data_crc32c=True, verified_digest_crc32c=False
    )
    # A digest-based algorithm on an EXTERNAL key signs the raw data.
    signer = self._new_signer(
        algorithm=_Algorithm.EC_SIGN_P256_SHA256,
        protection_level=protection_level,
    )

    self.assertEqual(signer.sign(_DATA), _SIGNATURE)

    request = client.asymmetric_sign.call_args.kwargs['request']
    self.assertEqual(request.data, _DATA)
    self.assertEqual(request.data_crc32c, google_crc32c.value(_DATA))
    self.assertEqual(request.digest.sha256, b'')


if __name__ == '__main__':
  absltest.main()
