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

"""Integration tests for the GCP KMS Mac primitive with the real Cloud KMS."""

import os

from absl.testing import absltest
from google.cloud import kms_v1
from google.oauth2 import service_account

from tink import core
from tink.integration import gcpkms
from tink.integration.gcpkms import _gcp_kms_mac
from tink.testing import helper

CREDENTIAL_PATH = os.path.join(
    helper.tink_py_testdata_path(), 'gcp/credential.json'
)

# MAC operations are bound to a specific CryptoKeyVersion, so the name includes
# the version.
KEY_NAME = 'projects/tink-test-infrastructure/locations/global/keyRings/unit-and-integration-testing/cryptoKeys/mac-key/cryptoKeyVersions/1'

DATA = b'This is some data to authenticate.'
OTHER_DATA = b'This is some other data.'

if 'TEST_SRCDIR' in os.environ:
  # Set root certificates for gRPC in Bazel Test which are needed on MacOS
  os.environ['GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'] = os.path.join(
      os.environ['TEST_SRCDIR'], 'google_root_pem/file/downloaded'
  )


class GcpKmsMacIntegrationTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIAL_PATH
    )
    cls.kms_client = kms_v1.KeyManagementServiceClient(credentials=credentials)
    cls.mac = gcpkms.new_gcp_kms_mac(KEY_NAME, cls.kms_client)

  @classmethod
  def tearDownClass(cls):
    # Closes the underlying transport explicitly.
    if hasattr(cls.kms_client, 'close'):
      cls.kms_client.close()
    elif hasattr(cls.kms_client, 'transport') and hasattr(
        cls.kms_client.transport, 'close'
    ):
      cls.kms_client.transport.close()
    super().tearDownClass()

  def test_compute_and_verify_mac_works(self):
    tag = self.mac.compute_mac(DATA)
    # Does not raise.
    self.mac.verify_mac(tag, DATA)

  def test_compute_and_verify_mac_max_data_size_works(self):
    max_data = b'a' * _gcp_kms_mac._MAX_MAC_DATA_SIZE
    tag = self.mac.compute_mac(max_data)
    # Does not raise.
    self.mac.verify_mac(tag, max_data)

  def test_compute_mac_is_deterministic(self):
    # HMAC is deterministic, and both calls are bound to the same
    # CryptoKeyVersion, so the two tags must be identical.
    self.assertEqual(self.mac.compute_mac(DATA), self.mac.compute_mac(DATA))

  def test_verify_mac_wrong_data_fails(self):
    tag = self.mac.compute_mac(DATA)
    # Cloud KMS reports that the MAC does not match, rather than failing the
    # RPC.
    with self.assertRaises(core.TinkError):
      self.mac.verify_mac(tag, OTHER_DATA)

  def test_verify_mac_modified_mac_fails(self):
    tag = self.mac.compute_mac(DATA)
    self.assertNotEmpty(tag)
    # Only flip a bit, so that the MAC keeps the length Cloud KMS expects.
    modified_tag = bytes([tag[0] ^ 0x01]) + tag[1:]
    with self.assertRaises(core.TinkError):
      self.mac.verify_mac(modified_tag, DATA)

  def test_verify_mac_truncated_mac_fails(self):
    tag = self.mac.compute_mac(DATA)
    self.assertNotEmpty(tag)
    # Cloud KMS rejects a MAC of the wrong length with an RPC error, the message
    # comes from the API, not from Tink.
    with self.assertRaises(core.TinkError):
      self.mac.verify_mac(tag[:-1], DATA)

  def test_compute_and_verify_mac_data_too_large_fails(self):
    too_large_data = b'a' * (_gcp_kms_mac._MAX_MAC_DATA_SIZE + 1)
    with self.assertRaises(core.TinkError):
      self.mac.compute_mac(too_large_data)
    with self.assertRaises(core.TinkError):
      self.mac.verify_mac(b'dummy_tag', too_large_data)

if __name__ == '__main__':
  absltest.main()
