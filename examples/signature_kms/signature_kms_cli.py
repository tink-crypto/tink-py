# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START gcp-kms-signature-example]

"""A command-line utility for signing and verifying files using Cloud KMS.

The private key never leaves Cloud KMS: signing is performed by Cloud KMS via
the AsymmetricSign RPC. Verification fetches the public key from Cloud KMS once,
when the verifier is built, and is then performed locally. Alternatively,
verification can be performed offline using a pre-fetched public key without any
Cloud KMS calls.
"""

import binascii
from collections.abc import Sequence
import enum

from absl import app
from absl import flags
from absl import logging
from google.cloud import kms_v1
from google.oauth2 import service_account
import tink
from tink.integration import gcpkms


class _Operation(enum.Enum):
  SIGN = 'sign'
  VERIFY = 'verify'
  VERIFY_OFFLINE = 'verify_offline'


_MODE = flags.DEFINE_enum_class(
    'mode',
    None,
    _Operation,
    'The operation to perform.',
    required=True,
)
_KEY_NAME = flags.DEFINE_string(
    'key_name',
    None,
    (
        'Resource name of the Cloud KMS CryptoKeyVersion, of the form '
        'projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*. '
        'Required for sign and verify modes.'
    ),
)
_GCP_CREDENTIAL_PATH = flags.DEFINE_string(
    'gcp_credential_path',
    None,
    'Path to a GCP credentials JSON file. Required for sign and verify modes.',
)
_DATA_PATH = flags.DEFINE_string(
    'data_path', None, 'Path to the file with the input data.', required=True
)
_SIGNATURE_PATH = flags.DEFINE_string(
    'signature_path', None, 'Path to the signature file.', required=True
)
_PUBLIC_KEY_PATH = flags.DEFINE_string(
    'public_key_path',
    None,
    (
        'Path to a file containing the pre-fetched public key (PEM or raw'
        ' bytes). Required for verify_offline mode.'
    ),
)
_ALGORITHM = flags.DEFINE_string(
    'algorithm',
    None,
    (
        'Name of the Cloud KMS CryptoKeyVersionAlgorithm (e.g., '
        'EC_SIGN_P256_SHA256). Required for verify_offline mode.'
    ),
)


def main(argv: Sequence[str]) -> int:
  del argv  # Unused.

  if _MODE.value in (_Operation.SIGN, _Operation.VERIFY):
    if not _KEY_NAME.value or not _GCP_CREDENTIAL_PATH.value:
      logging.error(
          '--key_name and --gcp_credential_path are required for mode %s.',
          _MODE.value.value,
      )
      return 1
  elif _MODE.value == _Operation.VERIFY_OFFLINE:
    if not _PUBLIC_KEY_PATH.value or not _ALGORITHM.value:
      logging.error(
          '--public_key_path and --algorithm are required for mode %s.',
          _MODE.value.value,
      )
      return 1

  try:
    with open(_DATA_PATH.value, 'rb') as data_file:
      data = data_file.read()
  except OSError as e:
    logging.exception('Error reading input data: %s', e)
    return 1

  kms_client = None
  if _MODE.value in (_Operation.SIGN, _Operation.VERIFY):
    # Create a Cloud KMS client using the given service account credentials.
    try:
      credentials = service_account.Credentials.from_service_account_file(
          _GCP_CREDENTIAL_PATH.value
      )
      kms_client = kms_v1.KeyManagementServiceClient(credentials=credentials)
    except (OSError, ValueError) as e:
      logging.exception('Error creating GCP KMS client: %s', e)
      return 1

  if _MODE.value == _Operation.SIGN:
    # Create a PublicKeySign primitive backed by Cloud KMS. This fetches the
    # public key once to determine the signing algorithm.
    try:
      signer = gcpkms.new_gcp_kms_public_key_sign(_KEY_NAME.value, kms_client)
      # Sign the data. The signature is written out hex-encoded.
      sig = signer.sign(data)
      with open(_SIGNATURE_PATH.value, 'wb') as signature_file:
        signature_file.write(binascii.hexlify(sig))
    except tink.TinkError as e:
      logging.exception('Tink error during signing process: %s', e)
      return 1
    except OSError as e:
      logging.exception('File error writing signature: %s', e)
      return 1
    return 0

  if _MODE.value == _Operation.VERIFY:
    # Create a PublicKeyVerify primitive backed by Cloud KMS. The public key is
    # fetched once when the verifier is built; verification is then performed
    # locally, with no further Cloud KMS calls.
    try:
      verifier = gcpkms.new_gcp_kms_public_key_verify(
          _KEY_NAME.value, kms_client
      )
    except tink.TinkError as e:
      logging.exception('Error creating primitive: %s', e)
      return 1
  else:
    # mode == 'verify_offline'.
    # Create a PublicKeyVerify primitive from a pre-fetched public key without
    # making any calls to Cloud KMS.
    try:
      with open(_PUBLIC_KEY_PATH.value, 'rb') as public_key_file:
        public_key = public_key_file.read()

      algorithm = getattr(
          kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm, _ALGORITHM.value
      )

      verifier = gcpkms.new_gcp_kms_public_key_verify_no_rpc(
          public_key, algorithm
      )
    except OSError as e:
      logging.exception('Error reading public key file: %s', e)
      return 1
    except AttributeError:
      logging.error('Unsupported KMS algorithm: %s', _ALGORITHM.value)
      return 1
    except tink.TinkError as e:
      logging.exception('Error creating primitive: %s', e)
      return 1

  try:
    with open(_SIGNATURE_PATH.value, 'rb') as signature_file:
      expected_signature = binascii.unhexlify(signature_file.read().strip())
  except (OSError, binascii.Error) as e:
    logging.exception('Error reading signature: %s', e)
    return 1

  try:
    verifier.verify(expected_signature, data)
    logging.info('Signature verification succeeded.')
    return 0
  except tink.TinkError:
    logging.info('Signature verification failed.')
    return 1


if __name__ == '__main__':
  app.run(main)
# [END gcp-kms-signature-example]
