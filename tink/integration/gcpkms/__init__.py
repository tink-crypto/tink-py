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

"""GCP KMS package."""

try:
  # pylint: disable=g-import-not-at-top
  from tink.integration.gcpkms import _gcp_kms_client
  from tink.integration.gcpkms import _gcp_kms_mac
  from tink.integration.gcpkms import _gcp_kms_public_key_sign
  from tink.integration.gcpkms import _gcp_kms_public_key_verify
except ImportError as import_error:
  raise ImportError(
      'Error importing the Tink Google Cloud KMS module; did you forget to'
      ' install the `tink[gcpkms]` extras?'
  ) from import_error

GcpKmsClient = _gcp_kms_client.GcpKmsClient
new_client = _gcp_kms_client.new_client
new_gcp_kms_mac = _gcp_kms_mac.new_gcp_kms_mac
new_gcp_kms_public_key_sign = (
    _gcp_kms_public_key_sign.new_gcp_kms_public_key_sign
)
new_gcp_kms_public_key_verify = (
    _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify
)
new_gcp_kms_public_key_verify_no_rpc = (
    _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc
)
