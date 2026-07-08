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
from google.cloud import kms_v1

from tink import core
from tink.integration.gcpkms import _gcp_kms_mac

KEY_VERSION = 'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1'
DATA = b'data for mac'
MAC = b'mac for data for mac'


class GcpKmsMacTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    absltest.mock.patch.object(kms_v1, 'KeyManagementServiceClient').start()

  def tearDown(self):
    absltest.mock.patch.stopall()
    super().tearDown()

  def test_create_gcp_kms_mac_works(self):
    gcp_mac = _gcp_kms_mac.new_gcp_kms_mac(
        KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )
    self.assertIsNotNone(gcp_mac)

  def test_methods_unimplemented(self):
    gcp_mac = _gcp_kms_mac.new_gcp_kms_mac(
        KEY_VERSION, kms_v1.KeyManagementServiceClient()
    )
    with self.assertRaises(core.TinkError):
      gcp_mac.compute_mac(DATA)
    with self.assertRaises(core.TinkError):
      gcp_mac.verify_mac(MAC, DATA)

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


if __name__ == '__main__':
  absltest.main()
