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

"""A Mac primitive backed by Google Cloud KMS."""

from google.cloud import kms_v1

import tink
from tink import mac
from tink.integration.gcpkms import _gcp_kms_util


class _GcpKmsMac(mac.Mac):
  """Implements the Mac interface for GCP KMS."""

  def __init__(
      self, client: kms_v1.KeyManagementServiceClient, key_name: str
  ) -> None:
    if not key_name:
      raise tink.TinkError('key_name cannot be null.')
    if not _gcp_kms_util.KMS_KEY_VERSION_REGEX.match(key_name):
      raise tink.TinkError(
          f'Invalid key_name format: {key_name}.\nMAC operations require a '
          'CryptoKeyVersion. KMS key versions should follow the format: '
          '"projects/<project-id>/locations/<location>/keyRings/<keyring>/'
          'cryptoKeys/<key-name>/cryptoKeyVersions/<version>"'
      )
    if not client:
      raise tink.TinkError('client cannot be null.')
    self._client = client
    self._name = key_name

  def compute_mac(self, data: bytes) -> bytes:
    raise tink.TinkError('Not implemented.')

  def verify_mac(self, mac_value: bytes, data: bytes) -> None:
    raise tink.TinkError('Not implemented.')


def new_gcp_kms_mac(
    key_name: str, kms_client: kms_v1.KeyManagementServiceClient
) -> mac.Mac:
  """Creates a Mac primitive backed by Google Cloud KMS.

  MAC computation and verification are forwarded to Cloud KMS via the MacSign
  and MacVerify RPCs.

  Args:
    key_name: The resource name of a CryptoKeyVersion in Cloud KMS, of the form
      "projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*" (see
      https://cloud.google.com/kms/docs/object-hierarchy). Note that, unlike the
      AEAD key URIs, this is the bare KMS resource name and is not prefixed with
      "gcp-kms://".
    kms_client: A google.cloud.kms_v1.KeyManagementServiceClient used to
      communicate with Cloud KMS.

  Returns:
    A Mac object.

  Raises:
    TinkError: If key_name is not a valid CryptoKeyVersion name or kms_client
      is None.
  """
  return _GcpKmsMac(kms_client, key_name)
