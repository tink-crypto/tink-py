# Copyright 2019 Google LLC
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

"""Tests for tink.python.tink.integration.gcp_kms_aead."""

import os
from unittest import mock

from absl.testing import absltest
from google.cloud import kms_v1
from google.oauth2 import service_account

import tink
from tink import aead
from tink.integration import gcpkms
from tink.testing import helper


CREDENTIAL_PATH = os.path.join(helper.tink_py_testdata_path(),
                               'gcp/credential.json')
KEY_URI = 'gcp-kms://projects/tink-test-infrastructure/locations/global/keyRings/unit-and-integration-testing/cryptoKeys/aead-key'
KEY_VERSION_URI = KEY_URI + '/cryptoKeyVersions/1'
LOCAL_KEY_URI = 'gcp-kms://projects/tink-test-infrastructure/locations/europe-west1/keyRings/unit-and-integration-test/cryptoKeys/aead-key'
BAD_KEY_URI = 'aws-kms://arn:aws:kms:us-east-2:235739564943:key/3ee50705-5a82-4f5b-9753-05c4f473922f'

KEY2_URI = 'gcp-kms://projects/tink-test-infrastructure/locations/global/keyRings/unit-and-integration-testing/cryptoKeys/aead2-key'

if 'TEST_SRCDIR' in os.environ:
  # Set root certificates for gRPC in Bazel Test which are needed on MacOS
  os.environ['GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'] = os.path.join(
      os.environ['TEST_SRCDIR'], 'google_root_pem/file/downloaded')


def setUpModule():
  aead.register()


class GcpKmsAeadTest(absltest.TestCase):

  def test_bound_to_key_uri_encrypt_decrypt(self):
    with gcpkms.GcpKmsClient(KEY_URI, CREDENTIAL_PATH) as gcp_client:
      self.assertTrue(gcp_client.does_support(KEY_URI))
      self.assertFalse(gcp_client.does_support(KEY2_URI))
      self.assertFalse(gcp_client.does_support(BAD_KEY_URI))

      gcp_aead = gcp_client.get_aead(KEY_URI)

      plaintext = b'plaintext'
      associated_data = b'associated_data'
      ciphertext = gcp_aead.encrypt(plaintext, associated_data)
      self.assertEqual(plaintext, gcp_aead.decrypt(ciphertext, associated_data))

      ciphertext = gcp_aead.encrypt(plaintext, b'')
      self.assertEqual(plaintext, gcp_aead.decrypt(ciphertext, b''))

      with self.assertRaises(tink.TinkError):
        gcp_client.get_aead(KEY2_URI)

  def test_not_bound_to_key_uri_encrypt_decrypt(self):
    with gcpkms.GcpKmsClient(None, CREDENTIAL_PATH) as gcp_client:
      self.assertTrue(gcp_client.does_support(KEY_URI))
      self.assertTrue(gcp_client.does_support(KEY2_URI))
      self.assertFalse(gcp_client.does_support(BAD_KEY_URI))

      plaintext = b'plaintext'
      associated_data = b'associated_data'

      gcp_aead = gcp_client.get_aead(KEY_URI)
      ciphertext = gcp_aead.encrypt(plaintext, associated_data)
      self.assertEqual(plaintext, gcp_aead.decrypt(ciphertext, associated_data))

      gcp_aead2 = gcp_client.get_aead(KEY_URI)
      ciphertext2 = gcp_aead2.encrypt(plaintext, associated_data)
      self.assertEqual(
          plaintext, gcp_aead2.decrypt(ciphertext2, associated_data)
      )

  def test_decrypt_with_wrong_ad_fails(self):
    with gcpkms.GcpKmsClient(KEY_URI, CREDENTIAL_PATH) as gcp_client:
      gcp_aead = gcp_client.get_aead(KEY_URI)

      ciphertext = gcp_aead.encrypt(b'plaintext', b'associated_data')
      with self.assertRaises(tink.TinkError):
        gcp_aead.decrypt(ciphertext, b'wrong_associated_data')

  def test_decrypt_with_wrong_key_fails(self):
    with gcpkms.GcpKmsClient(None, CREDENTIAL_PATH) as gcp_client:
      gcp_aead1 = gcp_client.get_aead(KEY_URI)
      gcp_aead2 = gcp_client.get_aead(KEY2_URI)

      ciphertext1 = gcp_aead1.encrypt(b'plaintext', b'associated_data')
      ciphertext2 = gcp_aead2.encrypt(b'plaintext', b'associated_data')

      # First, verify that both key URIs work.
      self.assertEqual(
          b'plaintext', gcp_aead1.decrypt(ciphertext1, b'associated_data')
      )
      self.assertEqual(
          b'plaintext', gcp_aead2.decrypt(ciphertext2, b'associated_data')
      )

      with self.assertRaises(tink.TinkError):
        gcp_aead2.decrypt(ciphertext1, b'associated_data')
      with self.assertRaises(tink.TinkError):
        gcp_aead1.decrypt(ciphertext2, b'associated_data')

  def test_encrypt_decrypt_localized_uri(self):
    with gcpkms.GcpKmsClient(LOCAL_KEY_URI, CREDENTIAL_PATH) as gcp_client:
      gcp_aead = gcp_client.get_aead(LOCAL_KEY_URI)

      plaintext = b'helloworld'
      ciphertext = gcp_aead.encrypt(plaintext, b'')
      self.assertEqual(plaintext, gcp_aead.decrypt(ciphertext, b''))

      plaintext = b'hello'
      associated_data = b'world'
      ciphertext = gcp_aead.encrypt(plaintext, associated_data)
      self.assertEqual(
          plaintext, gcp_aead.decrypt(ciphertext, associated_data)
      )

  def test_encrypt_with_bad_uri(self):
    with self.assertRaises(tink.TinkError):
      with gcpkms.GcpKmsClient(KEY_URI, CREDENTIAL_PATH) as gcp_client:
        gcp_client.get_aead(BAD_KEY_URI)

  def test_corrupted_ciphertext(self):
    with gcpkms.GcpKmsClient(KEY_URI, CREDENTIAL_PATH) as gcp_client:
      gcp_aead = gcp_client.get_aead(KEY_URI)

      plaintext = b'helloworld'
      ciphertext = gcp_aead.encrypt(plaintext, b'')
      self.assertEqual(plaintext, gcp_aead.decrypt(ciphertext, b''))

      # Corrupt each byte once and check that decryption fails
      # NOTE: Only starting at 4th byte here, as the 3rd byte is malleable
      #      (see b/146633745).
      for byte_idx in range(3, len(ciphertext)):
        tmp_ciphertext = list(ciphertext)
        tmp_ciphertext[byte_idx] ^= 1
        corrupted_ciphertext = bytes(tmp_ciphertext)
        with self.assertRaises(tink.TinkError):
          gcp_aead.decrypt(corrupted_ciphertext, b'')

  def test_init_with_credentials_and_credentials_path_fails(self):
    credentials = mock.Mock()
    with self.assertRaises(tink.TinkError):
      gcpkms.GcpKmsClient(KEY_URI, CREDENTIAL_PATH, credentials=credentials)

  def test_init_with_credentials_no_credentials_path(self):
    mock_client = mock.Mock()
    with mock.patch.object(
        kms_v1, 'KeyManagementServiceClient', return_value=mock_client
    ) as mock_kms_client_constructor:
      credentials = mock.Mock()
      with gcpkms.GcpKmsClient(KEY_URI, credentials=credentials):
        mock_kms_client_constructor.assert_called_with(credentials=credentials)

  def test_init_no_credentials_with_credentials_path(self):
    mock_client = mock.Mock()
    with mock.patch.object(
        kms_v1, 'KeyManagementServiceClient', return_value=mock_client
    ) as mock_kms_client_constructor:
      mock_credentials = mock.Mock()
      with mock.patch.object(
          service_account.Credentials,
          'from_service_account_file',
          return_value=mock_credentials,
      ):
        with gcpkms.GcpKmsClient(KEY_URI, CREDENTIAL_PATH):
          mock_kms_client_constructor.assert_called_with(
              credentials=mock_credentials
          )

  def test_init_no_credentials_no_credentials_path(self):
    mock_client = mock.Mock()
    with mock.patch.object(
        kms_v1, 'KeyManagementServiceClient', return_value=mock_client
    ) as mock_kms_client_constructor:
      with gcpkms.GcpKmsClient(KEY_URI):
        mock_kms_client_constructor.assert_called()

  def test_encrypt_decrypt_with_key_version_uri(self):
    with gcpkms.GcpKmsClient(KEY_VERSION_URI, CREDENTIAL_PATH) as gcp_client:
      self.assertTrue(gcp_client.does_support(KEY_VERSION_URI))

      gcp_aead = gcp_client.get_aead(KEY_VERSION_URI)

      plaintext = b'plaintext'
      associated_data = b'associated_data'
      # Encryption is supported.
      ciphertext = gcp_aead.encrypt(plaintext, associated_data)
      # Decrpytion is not.
      with self.assertRaises(tink.TinkError):
        gcp_aead.decrypt(ciphertext, associated_data)


if __name__ == '__main__':
  absltest.main()
