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

_EC_SIGN_ALGORITHM = (
    kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm.EC_SIGN_P256_SHA256
)


def _public_key_response(
    name: str = _KEY_VERSION,
    algorithm: kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm = _EC_SIGN_ALGORITHM,
    data: bytes = _PUBLIC_KEY_DATA,
    crc32c_checksum: int | None = None,
) -> kms_v1.types.PublicKey:
  if crc32c_checksum is None:
    crc32c_checksum = google_crc32c.value(data)
  return kms_v1.types.PublicKey(
      name=name,
      algorithm=algorithm,
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

  def _new_signer(self) -> _gcp_kms_public_key_sign._GcpKmsPublicKeySign:
    """Builds a signer, treating the test's default algorithm as supported."""
    with mock.patch.object(
        _gcp_kms_public_key_sign,
        '_SUPPORTED_ALGORITHMS',
        frozenset([_EC_SIGN_ALGORITHM]),
    ):
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
    # No algorithm is supported yet, so construction always fails the gate.
    with self.assertRaisesRegex(core.TinkError, r'is not supported'):
      _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign(
          _KEY_VERSION, kms_v1.KeyManagementServiceClient()
      )

  def test_get_public_key_rpc_fails(self):
    kms_v1.KeyManagementServiceClient().get_public_key.side_effect = (
        CustomException()
    )
    with self.assertRaises(core.TinkError):
      self._new_signer()

  def test_get_public_key_response_key_name_mismatch_fails(self):
    kms_v1.KeyManagementServiceClient().get_public_key.return_value = (
        _public_key_response(name=_OTHER_KEY_VERSION)
    )
    with self.assertRaisesRegex(
        core.TinkError,
        r'The key name in the GetPublicKey response does not match',
    ):
      self._new_signer()

  def test_get_public_key_checksum_mismatch_fails(self):
    kms_v1.KeyManagementServiceClient().get_public_key.return_value = (
        _public_key_response(crc32c_checksum=1)
    )
    with self.assertRaisesRegex(
        core.TinkError, r'The GetPublicKey checksum does not match'
    ):
      self._new_signer()

  def test_construction_succeeds_for_supported_algorithm(self):
    self.assertIsNotNone(self._new_signer())

  def test_sign_data_too_large_fails(self):
    signer = self._new_signer()
    with self.assertRaisesRegex(
        core.TinkError, r'The data size is larger than the allowed size'
    ):
      signer.sign(b'a' * (_gcp_kms_public_key_sign._MAX_SIGN_DATA_SIZE + 1))

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


if __name__ == '__main__':
  absltest.main()
