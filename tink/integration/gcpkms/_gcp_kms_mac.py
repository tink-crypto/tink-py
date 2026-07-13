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

from google.api_core import exceptions as core_exceptions
from google.cloud import kms_v1
import google_crc32c

import tink
from tink import mac
from tink.integration.gcpkms import _gcp_kms_util


# Maximum size of the data that can be used for MAC computation/verification.
_MAX_MAC_DATA_SIZE = 64 * 1024


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
    if len(data) > _MAX_MAC_DATA_SIZE:
      raise tink.TinkError(
          'The data size is larger than the allowed size:'
          f' {_MAX_MAC_DATA_SIZE}.'
      )
    try:
      response = self._client.mac_sign(
          request=kms_v1.MacSignRequest(
              name=self._name,
              data=data,
              data_crc32c=google_crc32c.value(data),
          )
      )
    except core_exceptions.GoogleAPIError as e:
      raise tink.TinkError(e) from e
    if response.name != self._name:
      raise tink.TinkError(
          'The key name in the response does not match the requested key name.'
      )
    if not response.verified_data_crc32c:
      raise tink.TinkError('Checking the input checksum failed.')
    if response.mac_crc32c != google_crc32c.value(response.mac):
      raise tink.TinkError('MAC checksum mismatch.')
    return response.mac

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
