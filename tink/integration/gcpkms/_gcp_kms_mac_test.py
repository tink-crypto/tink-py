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

from absl.testing import absltest
from absl.testing import parameterized
from google.api_core import exceptions as core_exceptions
from google.cloud import kms_v1
import google_crc32c

from tink import core
from tink.integration.gcpkms import _gcp_kms_mac

KEY_VERSION = 'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1'
OTHER_KEY_VERSION = 'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/2'
DATA = b'data for mac'
MAC = b'mac for data for mac'


class CustomException(core_exceptions.GoogleAPIError):
  pass


def _mac_sign_response(
    name: str = KEY_VERSION,
    mac: bytes = MAC,
    verified_data_crc32c: bool = True,
    mac_crc32c: int | None = None,
) -> kms_v1.types.MacSignResponse:
  if mac_crc32c is None:
    mac_crc32c = google_crc32c.value(mac)
  return kms_v1.types.MacSignResponse(
      name=name,
      mac=mac,
      verified_data_crc32c=verified_data_crc32c,
      mac_crc32c=mac_crc32c,
  )


class GcpKmsMacTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    absltest.mock.patch.object(kms_v1, 'KeyManagementServiceClient').start()

  def tearDown(self):
    absltest.mock.patch.stopall()
    super().tearDown()

  def test_client_null(self):
    with self.assertRaises(core.TinkError):
      _gcp_kms_mac.new_gcp_kms_mac(KEY_VERSION, None)

  @parameterized.parameters(
      '',
      None,
      'wrong/kms/key/format',
      # A CryptoKey is not enough; MAC requires a CryptoKeyVersion.
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1',
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions',
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1/',
      'gcp-kms://projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1',
  )
  def test_key_name_format_wrong(self, key_name):
    with self.assertRaises(core.TinkError):
      _gcp_kms_mac.new_gcp_kms_mac(
          key_name, kms_v1.KeyManagementServiceClient()
      )

  def test_compute_mac_works(self):
    kms_v1.KeyManagementServiceClient().mac_sign.return_value = (
        _mac_sign_response()
    )
    gcp_mac = _gcp_kms_mac.new_gcp_kms_mac(
        KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )
    self.assertEqual(gcp_mac.compute_mac(DATA), MAC)

  def test_compute_mac_rpc_fails(self):
    kms_v1.KeyManagementServiceClient().mac_sign.side_effect = CustomException()
    gcp_mac = _gcp_kms_mac.new_gcp_kms_mac(
        KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )
    with self.assertRaises(core.TinkError):
      gcp_mac.compute_mac(DATA)

  def test_compute_mac_response_key_name_mismatch_fails(self):
    kms_v1.KeyManagementServiceClient().mac_sign.return_value = (
        _mac_sign_response(name=OTHER_KEY_VERSION)
    )
    gcp_mac = _gcp_kms_mac.new_gcp_kms_mac(
        KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )
    with self.assertRaises(core.TinkError):
      gcp_mac.compute_mac(DATA)

  def test_compute_mac_data_crc32c_not_verified_fails(self):
    kms_v1.KeyManagementServiceClient().mac_sign.return_value = (
        _mac_sign_response(verified_data_crc32c=False)
    )
    gcp_mac = _gcp_kms_mac.new_gcp_kms_mac(
        KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )
    with self.assertRaises(core.TinkError):
      gcp_mac.compute_mac(DATA)

  def test_compute_mac_mac_crc32c_mismatch_fails(self):
    kms_v1.KeyManagementServiceClient().mac_sign.return_value = (
        _mac_sign_response(mac_crc32c=1)
    )
    gcp_mac = _gcp_kms_mac.new_gcp_kms_mac(
        KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )
    with self.assertRaises(core.TinkError):
      gcp_mac.compute_mac(DATA)

  def test_compute_mac_data_too_large_fails(self):
    gcp_mac = _gcp_kms_mac.new_gcp_kms_mac(
        KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )
    with self.assertRaises(core.TinkError):
      gcp_mac.compute_mac(b'a' * (_gcp_kms_mac._MAX_MAC_DATA_SIZE + 1))


if __name__ == '__main__':
  absltest.main()
