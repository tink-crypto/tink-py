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

"""Shared utilities for the Google Cloud KMS integration."""

import re

import tink

# Matches the resource name of a CryptoKeyVersion in Cloud KMS.
KMS_KEY_VERSION_REGEX = re.compile(
    'projects/([^/]+)/'
    'locations/([a-zA-Z0-9_-]{1,63})/'
    'keyRings/([a-zA-Z0-9_-]{1,63})/'
    'cryptoKeys/([a-zA-Z0-9_-]{1,63})/'
    'cryptoKeyVersions/([a-zA-Z0-9_-]{1,63})$'
)


def validate_kms_key_name(key_name: str) -> None:
  """Validates that key_name is a valid Cloud KMS CryptoKeyVersion name.

  MAC and Signing operations require a CryptoKeyVersion. See
  https://cloud.google.com/kms/docs/object-hierarchy.

  Args:
    key_name: The KMS key resource name to validate.

  Raises:
    tink.TinkError: If key_name is null or does not match the expected format
    for key versions.
  """
  if not key_name:
    raise tink.TinkError('key_name cannot be null.')
  if not KMS_KEY_VERSION_REGEX.match(key_name):
    raise tink.TinkError(
        f'Invalid key_name format: {key_name}. This operation requires'
        ' a CryptoKeyVersion. KMS key versions should follow the format:'
        ' "projects/<project-id>/locations/<location>/keyRings/<keyring>/'
        'cryptoKeys/<key-name>/cryptoKeyVersions/<version>"'
    )

