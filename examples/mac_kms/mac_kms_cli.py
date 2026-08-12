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

# [START gcp-kms-mac-example]

"""A command-line utility for computing and verifying MACs using Cloud KMS.

MAC computation and verification are both forwarded to Cloud KMS via the MacSign
and MacVerify RPCs; the key never leaves Cloud KMS.
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
  COMPUTE = 'compute'
  VERIFY = 'verify'


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
        'Resource name of the Cloud KMS CryptoKeyVersion, of the form'
        ' projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*.'
        ' Note that, unlike the AEAD key URIs, this is the bare KMS resource'
        ' name and is not prefixed with "gcp-kms://".'
    ),
    required=True,
)
_GCP_CREDENTIAL_PATH = flags.DEFINE_string(
    'gcp_credential_path',
    None,
    'Path to the GCP credentials JSON file.',
    required=True,
)
_DATA_PATH = flags.DEFINE_string(
    'data_path', None, 'Path to the file with the input data.', required=True
)
_MAC_PATH = flags.DEFINE_string(
    'mac_path', None, 'Path to the MAC file.', required=True
)


def main(argv: Sequence[str]) -> int:
  del argv  # Unused.

  try:
    with open(_DATA_PATH.value, 'rb') as data_file:
      data = data_file.read()
  except OSError as e:
    logging.exception('Error reading input data: %s', e)
    return 1

  # Create a Cloud KMS client using the given service account credentials.
  try:
    credentials = service_account.Credentials.from_service_account_file(
        _GCP_CREDENTIAL_PATH.value
    )
    kms_client = kms_v1.KeyManagementServiceClient(credentials=credentials)
  except (OSError, ValueError) as e:
    logging.exception('Error creating GCP KMS client: %s', e)
    return 1

  # Create a Mac primitive backed by Cloud KMS. Both compute_mac and verify_mac
  # are forwarded to Cloud KMS; the key never leaves Cloud KMS.
  try:
    mac_primitive = gcpkms.new_gcp_kms_mac(_KEY_NAME.value, kms_client)
  except tink.TinkError as e:
    logging.exception('Error creating primitive: %s', e)
    return 1

  if _MODE.value == _Operation.COMPUTE:
    # Compute the MAC. The tag is written out hex-encoded.
    try:
      tag = mac_primitive.compute_mac(data)
      with open(_MAC_PATH.value, 'wb') as mac_file:
        mac_file.write(binascii.hexlify(tag))
    except tink.TinkError as e:
      logging.exception('Tink error during MAC computation: %s', e)
      return 1
    except OSError as e:
      logging.exception('File error writing tag: %s', e)
      return 1
    return 0

  # mode == 'verify'.
  try:
    with open(_MAC_PATH.value, 'rb') as mac_file:
      expected_tag = binascii.unhexlify(mac_file.read().strip())
  except (OSError, binascii.Error) as e:
    logging.exception('Error reading MAC: %s', e)
    return 1

  try:
    mac_primitive.verify_mac(expected_tag, data)
    logging.info('MAC verification succeeded.')
    return 0
  except tink.TinkError:
    logging.info('MAC verification failed.')
    return 1


if __name__ == '__main__':
  app.run(main)
# [END gcp-kms-mac-example]
