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
"""Tests for tink.python.tink.integration.aws_kms_aead."""

import os

from absl.testing import absltest
import boto3

import tink
from tink import _kms_clients
from tink import aead
from tink.integration import awskms
from tink.integration.awskms import _aws_kms_client
from tink.testing import helper


CREDENTIAL_PATH = os.path.join(helper.tink_py_testdata_path(),
                               'aws/credentials.ini')

BAD_CREDENTIALS_PATH = os.path.join(helper.tink_py_testdata_path(),
                                    'aws/credentials_bad.ini')

KEY_URI = ('aws-kms://arn:aws:kms:us-east-2:235739564943:key/'
           '3ee50705-5a82-4f5b-9753-05c4f473922f')

# An alias for KEY_URI.
KEY_ALIAS_URI = ('aws-kms://arn:aws:kms:us-east-2:235739564943:alias/'
                 'unit-and-integration-testing')

KEY_URI_2 = ('aws-kms://arn:aws:kms:us-east-2:235739564943:key/'
             'b3ca2efd-a8fb-47f2-b541-7e20f8c5cd11')

GCP_KEY_URI = ('gcp-kms://projects/tink-test-infrastructure/locations/global/'
               'keyRings/unit-and-integration-testing/cryptoKeys/aead-key')


def setUpModule():
  aead.register()


class AwsKmsAeadTest(absltest.TestCase):

  def tearDown(self):
    super().tearDown()
    _kms_clients.reset_kms_clients()

  def test_encrypt_decrypt(self):
    aws_client = awskms.AwsKmsClient(KEY_URI, CREDENTIAL_PATH)
    aws_aead = aws_client.get_aead(KEY_URI)

    plaintext = b'hello'
    associated_data = b'world'
    ciphertext = aws_aead.encrypt(plaintext, associated_data)
    self.assertEqual(plaintext, aws_aead.decrypt(ciphertext, associated_data))

    plaintext = b'hello'
    ciphertext = aws_aead.encrypt(plaintext, b'')
    self.assertEqual(plaintext, aws_aead.decrypt(ciphertext, b''))

  def test_encrypt_decrypt_with_key_alias(self):
    aws_client = awskms.AwsKmsClient(KEY_ALIAS_URI, CREDENTIAL_PATH)
    aws_aead = aws_client.get_aead(KEY_ALIAS_URI)

    plaintext = b'hello'
    associated_data = b'world'
    ciphertext = aws_aead.encrypt(plaintext, associated_data)
    self.assertEqual(plaintext, aws_aead.decrypt(ciphertext, associated_data))

    plaintext = b'hello'
    ciphertext = aws_aead.encrypt(plaintext, b'')
    self.assertEqual(plaintext, aws_aead.decrypt(ciphertext, b''))

  def test_corrupted_ciphertext(self):
    aws_client = awskms.AwsKmsClient(KEY_URI, CREDENTIAL_PATH)
    aws_aead = aws_client.get_aead(KEY_URI)

    plaintext = b'helloworld'
    ciphertext = aws_aead.encrypt(plaintext, b'')
    self.assertEqual(plaintext, aws_aead.decrypt(ciphertext, b''))

    # Corrupt each byte once and check that decryption fails
    # NOTE: Skipping two bytes as they are malleable
    for byte_idx in [b for b in range(len(ciphertext)) if b not in [77, 123]]:
      tmp_ciphertext = list(ciphertext)
      tmp_ciphertext[byte_idx] ^= 1
      corrupted_ciphertext = bytes(tmp_ciphertext)
      with self.assertRaises(tink.TinkError):
        aws_aead.decrypt(corrupted_ciphertext, b'')

  def test_encrypt_with_bad_uri(self):
    with self.assertRaises(tink.TinkError):
      aws_client = awskms.AwsKmsClient(KEY_URI, CREDENTIAL_PATH)
      aws_client.get_aead(GCP_KEY_URI)

  def test_encrypt_with_bad_credentials(self):
    aws_client = awskms.AwsKmsClient(KEY_URI, BAD_CREDENTIALS_PATH)
    aws_aead = aws_client.get_aead(KEY_URI)

    plaintext = b'hello'
    associated_data = b'world'
    with self.assertRaises(tink.TinkError):
      aws_aead.encrypt(plaintext, associated_data)

  def test_new_client_get_aead(self):
    aws_access_key_id, aws_secret_access_key = _aws_kms_client._parse_config(
        CREDENTIAL_PATH
    )
    boto3_client = boto3.client(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name='us-east-2',
        service_name='kms',
    )

    aws_client = awskms.new_client(boto3_client=boto3_client)

    aws_aead = aws_client.get_aead(KEY_URI)
    ciphertext = aws_aead.encrypt(b'plaintext', b'associated_data')
    self.assertEqual(
        b'plaintext', aws_aead.decrypt(ciphertext, b'associated_data')
    )

    aws_aead_with_alias = aws_client.get_aead(KEY_ALIAS_URI)
    ciphertext = aws_aead_with_alias.encrypt(b'plaintext', b'associated_data')
    self.assertEqual(
        b'plaintext',
        aws_aead_with_alias.decrypt(ciphertext, b'associated_data'),
    )

    with self.assertRaises(tink.TinkError):
      aws_client.get_aead(GCP_KEY_URI)

  def test_client_registration(self):
    # Register AWS KMS Client bound to KEY_URI.
    awskms.AwsKmsClient.register_client(KEY_URI, CREDENTIAL_PATH)

    # Create a keyset handle for KEY_URI and use it.
    handle = tink.new_keyset_handle(
        aead.aead_key_templates.create_kms_aead_key_template(KEY_URI)
    )
    aws_aead = handle.primitive(aead.Aead)
    ciphertext = aws_aead.encrypt(b'plaintext', b'associated_data')
    self.assertEqual(
        b'plaintext', aws_aead.decrypt(ciphertext, b'associated_data')
    )

    # It fails for any other key URI.
    with self.assertRaises(tink.TinkError):
      handle2 = tink.new_keyset_handle(
          aead.aead_key_templates.create_kms_aead_key_template(KEY_URI_2)
      )
      gcp_aead = handle2.primitive(aead.Aead)
      gcp_aead.encrypt(b'plaintext', b'associated_data')

  def test_get_aead_is_compatible_with_kms_aead_key(self):
    # Get Aead directly from AwsKmsClient
    aws_aead = awskms.AwsKmsClient(KEY_URI, CREDENTIAL_PATH).get_aead(KEY_URI)

    # Use KmsAeadKey: Register client, create keyset and then Aead.
    awskms.AwsKmsClient.register_client(KEY_URI, CREDENTIAL_PATH)
    handle = tink.new_keyset_handle(
        aead.aead_key_templates.create_kms_aead_key_template(KEY_URI)
    )
    aead_from_kms_aead_key = handle.primitive(aead.Aead)

    # check that they are compatible.
    ciphertext = aws_aead.encrypt(b'plaintext', b'associated_data')
    self.assertEqual(
        b'plaintext',
        aead_from_kms_aead_key.decrypt(ciphertext, b'associated_data'),
    )

  def test_encrypt_with_default_credentials(self):
    # If no credentials_path is provided, this path here is used by default.
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = CREDENTIAL_PATH

    aws_client = awskms.AwsKmsClient(key_uri=KEY_URI, credentials_path=None)
    aws_aead = aws_client.get_aead(KEY_URI)

    ciphertext = aws_aead.encrypt(b'plaintext', b'associated_data')
    self.assertEqual(
        b'plaintext', aws_aead.decrypt(ciphertext, b'associated_data')
    )

    # creates a boto3 client using default credentials
    boto3_client = boto3.client(region_name='us-east-2', service_name='kms')
    aws_client2 = awskms.new_client(boto3_client=boto3_client, key_uri=KEY_URI)
    aws_aead2 = aws_client2.get_aead(KEY_URI)
    ciphertext2 = aws_aead2.encrypt(b'plaintext', b'associated_data')
    self.assertEqual(
        b'plaintext', aws_aead2.decrypt(ciphertext2, b'associated_data')
    )

    # check that aws_aead and aws_aead2 are compatible
    self.assertEqual(
        b'plaintext', aws_aead2.decrypt(ciphertext, b'associated_data')
    )
    self.assertEqual(
        b'plaintext', aws_aead.decrypt(ciphertext2, b'associated_data')
    )

  def test_server_side_key_commitment(self):
    key1_client = awskms.AwsKmsClient(KEY_URI, CREDENTIAL_PATH)
    key1_aead = key1_client.get_aead(KEY_URI)

    alias_client = awskms.AwsKmsClient(KEY_ALIAS_URI, CREDENTIAL_PATH)
    alias_aead = alias_client.get_aead(KEY_ALIAS_URI)

    key2_client = awskms.AwsKmsClient(KEY_URI_2, CREDENTIAL_PATH)
    key2_aead = key2_client.get_aead(KEY_URI_2)

    plaintext = b'hello'
    associated_data = b'world'

    # Confirm that KEY_URI and KEY_ALIAS_URI are interchangeable while the
    # KEY_ALIAS_URI continues to reference KEY_URI. This no longer holds if
    # KEY_ALIAS_URI is updated to reference a different key.
    for a in (key1_aead, alias_aead):
      ciphertext = a.encrypt(plaintext, associated_data)

      # Decrypt with KEY_URI.
      self.assertEqual(
          plaintext, key1_aead.decrypt(ciphertext, associated_data)
      )

      # Decrypt with KEY_ALIAS_URI.
      self.assertEqual(
          plaintext, alias_aead.decrypt(ciphertext, associated_data)
      )

      # Attempt to decrypt with KEY_URI_2.
      with self.assertRaises(tink.TinkError):
        key2_aead.decrypt(ciphertext, associated_data)

  def test_kms_behavior(self):
    aws_aead = awskms.AwsKmsClient(KEY_URI, CREDENTIAL_PATH).get_aead(KEY_URI)
    plaintext = b'hello'
    associated_data = b'world'
    ciphertext = aws_aead.encrypt(plaintext, associated_data)

    # NOTE: The following operations directly utilize the KMS client to verify
    # KMS behavior for requests not produced by this implementation (e.g. no
    # KeyId specified, inspecting response fields).

    encryption_context = _aws_kms_client._encryption_context(associated_data)

    # Verify key ID contained in the reponse. AWS KMS includes resolved key IDs
    # in responses, not aliases. This behavior precludes client-side key
    # commitment checking.
    response = aws_aead.client.decrypt(
        KeyId=_aws_kms_client._key_uri_to_key_arn(KEY_ALIAS_URI),
        CiphertextBlob=ciphertext,
        EncryptionContext=encryption_context,
    )
    self.assertEqual(plaintext, response['Plaintext'])
    self.assertEqual(
        _aws_kms_client._key_uri_to_key_arn(KEY_URI), response['KeyId']
    )

    # Decrypt without specifying a key ID in the request. Decrypt requests
    # produced by this library always include a key ID to trigger server side
    # key commitment checks.
    response = aws_aead.client.decrypt(
        CiphertextBlob=ciphertext,
        EncryptionContext=encryption_context,
    )
    self.assertEqual(plaintext, response['Plaintext'])


if __name__ == '__main__':
  absltest.main()
