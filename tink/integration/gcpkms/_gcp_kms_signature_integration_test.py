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

"""Integration tests for the GCP KMS signature primitives with Cloud KMS."""

import os
import textwrap

from absl.testing import absltest
from absl.testing import parameterized
from google.cloud import kms_v1
from google.oauth2 import service_account

from tink import core
from tink.integration import gcpkms
from tink.integration.gcpkms import _gcp_kms_public_key_sign
from tink.integration.gcpkms import _gcp_kms_util
from tink.testing import helper

CREDENTIAL_PATH = os.path.join(
    helper.tink_py_testdata_path(), 'gcp/credential.json'
)

# KMS key ring hosted in the Google Cloud project `tink-test-infrastructure`,
# used for Tink integration tests.
KEY_VERSION_NAME_PREFIX = 'projects/tink-test-infrastructure/locations/global/keyRings/unit-and-integration-testing/cryptoKeys/'

# Cloud KMS asymmetric-sign keys to test, as (test name, CryptoKey) pairs.
SIGNATURE_KEYS = [
    ('ecdsa_p256_sha256', 'signature-key'),
    ('rsa_pss_2048_sha256', 'rsa-pss-2048-key'),
    ('ml_dsa_65', 'ml-dsa-65-key'),
    ('ml_dsa_65_external_mu', 'ml-dsa-65-external-mu-key'),
    ('slh_dsa_sha2_128s', 'slh-dsa-128s-key'),
]

# The subset of SIGNATURE_KEYS for which Cloud KMS signs the message itself
# rather than a digest of it, so that the client-side maximum data size applies.
_SIGNATURE_KEYS_DICT = dict(SIGNATURE_KEYS)

DATA_BASED_SIGNATURE_KEYS = [
    (k, _SIGNATURE_KEYS_DICT[k])
    for k in [
        'ml_dsa_65',
        'slh_dsa_sha2_128s',
    ]
]

DATA = b'This is some message to sign.'
OTHER_DATA = b'This is some other message.'

_OTHER_ECDSA_P256_PEM = textwrap.dedent("""\
    -----BEGIN PUBLIC KEY-----
    MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEPu+j4MR6Veo9F2YyKq0AObMM3UoN
    K4Z6V0tej/9smL+QfqkILtkY0DROmBbLb/tOg+zi/q6CAG5FuBK7CaZP0g==
    -----END PUBLIC KEY-----
    """).encode('utf-8')

if 'TEST_SRCDIR' in os.environ:
  # Set root certificates for gRPC in Bazel Test which are needed on MacOS
  os.environ['GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'] = os.path.join(
      os.environ['TEST_SRCDIR'], 'google_root_pem/file/downloaded'
  )


def _key_version_name(crypto_key: str) -> str:
  """Returns the resource name of version 1 of crypto_key.

  Asymmetric signing is bound to a specific CryptoKeyVersion, so the version is
  part of the name.

  Args:
    crypto_key: The CryptoKey in KEY_VERSION_NAME_PREFIX to build the name for.

  Returns:
    The resource name of the CryptoKeyVersion.
  """
  return KEY_VERSION_NAME_PREFIX + crypto_key + '/cryptoKeyVersions/1'


class GcpKmsSignatureIntegrationTest(parameterized.TestCase):
  kms_client: kms_v1.KeyManagementServiceClient

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIAL_PATH
    )
    cls.kms_client = kms_v1.KeyManagementServiceClient(credentials=credentials)

  @classmethod
  def tearDownClass(cls):
    # Closes the underlying transport explicitly.
    cls.kms_client.close()
    super().tearDownClass()

  def _signer(self, crypto_key):
    """Returns a signer that signs with the Cloud KMS key under test."""
    return gcpkms.new_gcp_kms_public_key_sign(
        _key_version_name(crypto_key), self.kms_client
    )

  def _verifier(self, crypto_key):
    """Returns a verifier for the public key Cloud KMS serves for the key."""
    return gcpkms.new_gcp_kms_public_key_verify(
        _key_version_name(crypto_key), self.kms_client
    )

  @parameterized.named_parameters(*SIGNATURE_KEYS)
  def test_sign_and_verify_works(self, crypto_key):
    signature = self._signer(crypto_key).sign(DATA)
    # Does not raise.
    self._verifier(crypto_key).verify(signature, DATA)

  @parameterized.named_parameters(*SIGNATURE_KEYS)
  def test_verify_modified_message_fails(self, crypto_key):
    signature = self._signer(crypto_key).sign(DATA)
    verifier = self._verifier(crypto_key)
    with self.assertRaises(core.TinkError):
      verifier.verify(signature, OTHER_DATA)

  @parameterized.named_parameters(*SIGNATURE_KEYS)
  def test_verify_modified_signature_fails(self, crypto_key):
    signature = self._signer(crypto_key).sign(DATA)
    self.assertNotEmpty(signature)
    # Only flip a bit, so that the signature keeps the expected length.
    modified_signature = signature[:-1] + bytes([signature[-1] ^ 0x01])
    verifier = self._verifier(crypto_key)
    with self.assertRaises(core.TinkError):
      verifier.verify(modified_signature, DATA)

  @parameterized.named_parameters(*SIGNATURE_KEYS)
  def test_verify_truncated_signature_fails(self, crypto_key):
    signature = self._signer(crypto_key).sign(DATA)
    self.assertNotEmpty(signature)
    verifier = self._verifier(crypto_key)
    with self.assertRaises(core.TinkError):
      verifier.verify(signature[:-1], DATA)

  @parameterized.named_parameters(*SIGNATURE_KEYS)
  def test_verify_offline_works(self, crypto_key):
    signature = self._signer(crypto_key).sign(DATA)

    # Fetch the public key material, then build a verifier from it without
    # further calls to Cloud KMS. GetPublicKey returns the material in the
    # format the offline verifier expects.
    public_key = _gcp_kms_util.fetch_public_key(
        self.kms_client, _key_version_name(crypto_key)
    )
    verifier = gcpkms.new_gcp_kms_public_key_verify_no_rpc(
        public_key.public_key.data, public_key.algorithm
    )

    # Does not raise.
    verifier.verify(signature, DATA)
    with self.assertRaises(core.TinkError):
      verifier.verify(signature, OTHER_DATA)

  def test_verify_offline_wrong_key_fails(self):
    crypto_key = 'signature-key'
    signature = self._signer(crypto_key).sign(DATA)

    verifier = gcpkms.new_gcp_kms_public_key_verify_no_rpc(
        _OTHER_ECDSA_P256_PEM,
        kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm.EC_SIGN_P256_SHA256
    )

    with self.assertRaises(core.TinkError):
      verifier.verify(signature, DATA)

  @parameterized.named_parameters(*DATA_BASED_SIGNATURE_KEYS)
  def test_sign_and_verify_max_data_size_works(self, crypto_key):
    max_data = b'a' * _gcp_kms_public_key_sign._MAX_SIGN_DATA_SIZE
    signature = self._signer(crypto_key).sign(max_data)
    # Does not raise.
    self._verifier(crypto_key).verify(signature, max_data)

  @parameterized.named_parameters(*DATA_BASED_SIGNATURE_KEYS)
  def test_sign_data_too_large_fails(self, crypto_key):
    too_large_data = b'a' * (_gcp_kms_public_key_sign._MAX_SIGN_DATA_SIZE + 1)
    with self.assertRaises(core.TinkError):
      self._signer(crypto_key).sign(too_large_data)


if __name__ == '__main__':
  absltest.main()
