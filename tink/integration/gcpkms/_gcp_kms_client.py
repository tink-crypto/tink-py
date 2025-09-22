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
"""A client for Google Cloud KMS."""

import re
from typing import Optional

from google.api_core import exceptions as core_exceptions
from google.auth import credentials as auth_credentials
from google.cloud import kms_v1
from google.oauth2 import service_account

import tink
from tink import aead

GCP_KEYURI_PREFIX = 'gcp-kms://'
_KMS_KEY_REGEX = re.compile(
    'projects/([^/]+)/'
    'locations/([a-zA-Z0-9_-]{1,63})/'
    'keyRings/([a-zA-Z0-9_-]{1,63})/'
    'cryptoKeys/([a-zA-Z0-9_-]{1,63})$'
)
_KMS_KEY_VERSION_REGEX = re.compile(
    'projects/([^/]+)/'
    'locations/([a-zA-Z0-9_-]{1,63})/'
    'keyRings/([a-zA-Z0-9_-]{1,63})/'
    'cryptoKeys/([a-zA-Z0-9_-]{1,63})/'
    'cryptoKeyVersions/([a-zA-Z0-9_-]{1,63})$'
)


class _GcpKmsAead(aead.Aead):
  """Implements the Aead interface for GCP KMS."""

  def __init__(
      self, client: kms_v1.KeyManagementServiceClient, key_name: str
  ) -> None:
    if not key_name:
      raise tink.TinkError('key_name cannot be null.')
    if not (
        _KMS_KEY_REGEX.match(key_name) or _KMS_KEY_VERSION_REGEX.match(key_name)
    ):
      raise tink.TinkError(
          'Invalid key_name format: {}.\nKMS keys should follow the format: '
          '"projects/<project-id>/locations/<location>/keyRings/<keyring>/'
          'cryptoKeys/<key-name>"'.format(key_name)
      )
    if not client:
      raise tink.TinkError('client cannot be null.')
    self.client = client
    self.name = key_name
    self.key_version_specified = bool(_KMS_KEY_VERSION_REGEX.match(key_name))

  def encrypt(self, plaintext: bytes, associated_data: bytes) -> bytes:
    try:
      response = self.client.encrypt(
          request=kms_v1.types.service.EncryptRequest(
              name=self.name,
              plaintext=plaintext,
              additional_authenticated_data=associated_data,
          )
      )
      return response.ciphertext
    except core_exceptions.GoogleAPIError as e:
      raise tink.TinkError(e)

  def decrypt(self, ciphertext: bytes, associated_data: bytes) -> bytes:
    if self.key_version_specified:
      raise tink.TinkError(
          'A CryptoKeyVersion was specified. Decryption is only supported when '
          'a CryptoKey is specified.'
      )
    try:
      response = self.client.decrypt(
         request=kms_v1.types.service.DecryptRequest(
             name=self.name,
             ciphertext=ciphertext,
             additional_authenticated_data=associated_data
         )
      )
      return response.plaintext
    except core_exceptions.GoogleAPIError as e:
      raise tink.TinkError(e)


class GcpKmsClient(tink.KmsClient):
  """Basic GCP client for AEAD."""

  def __init__(
      self,
      key_uri: Optional[str],
      credentials_path: Optional[str] = None,
      *,
      credentials: Optional[auth_credentials.Credentials] = None,
  ) -> None:
    """Creates a new GcpKmsClient that is bound to the key specified in 'key_uri'.

    Uses the specified credentials when communicating with the KMS. If neither
    credentials_path nor credentials are specified, the client will attempt to
    ascertain credentials from the environment.

    The key_uri can either by a CryptoKey or a CryptoKeyVersion. If a CryptoKey
    is specified, both encryption and decryption operations are supported. If a
    CryptoKeyVersion is specified, only encryption operations are supported.

    Args:
      key_uri: The URI of the key the client should be bound to. If it is None
        or empty, then the client is not bound to any particular key.
      credentials_path: Path to the file with the access credentials.
      credentials: The authorization credentials to attach to requests. This
        argument is mutually exclusive with credentials_path.

    Raises:
      ValueError: If the path or filename of the credentials is invalid.
      TinkError: If the key uri is not valid.
    """

    if not key_uri:
      self._key_uri = None
    elif key_uri.startswith(GCP_KEYURI_PREFIX):
      self._key_uri = key_uri
    else:
      raise tink.TinkError('Invalid key_uri.')
    if credentials and credentials_path:
      raise tink.TinkError(
          'Only one of credentials and credentials_path can be set.'
      )
    if not credentials and credentials_path:
      credentials = service_account.Credentials.from_service_account_file(
          credentials_path
      )
    self._client = kms_v1.KeyManagementServiceClient(credentials=credentials)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if hasattr(self._client, '__exit__'):
      self._client.__exit__(exc_type, exc_value, traceback)
    elif hasattr(self._client, 'transport'):
      self._client.transport.channel.close()

  def does_support(self, key_uri: str) -> bool:
    """Returns true iff this client supports KMS key specified in 'key_uri'.

    Args:
      key_uri: URI of the key to be checked.

    Returns:
      A boolean value which is true if the key is supported and false otherwise.
    """
    if not self._key_uri:
      return key_uri.startswith(GCP_KEYURI_PREFIX)
    return key_uri == self._key_uri

  def get_aead(self, key_uri: str) -> aead.Aead:
    """Returns an Aead-primitive backed by KMS key specified by 'key_uri'.

    Args:
      key_uri: URI of the key which should be used.

    Returns:
      An Aead object.
    """
    if self._key_uri and self._key_uri != key_uri:
      raise tink.TinkError(
          'This client is bound to %s and cannot use key %s'
          % (self._key_uri, key_uri)
      )
    if not key_uri.startswith(GCP_KEYURI_PREFIX):
      raise tink.TinkError('Invalid key_uri.')
    key_id = key_uri[len(GCP_KEYURI_PREFIX) :]
    return _GcpKmsAead(self._client, key_id)

  @classmethod
  def register_client(
      cls, key_uri: Optional[str], credentials_path: Optional[str]
  ) -> None:
    """Add a new KMS client to the global list of KMS clients.

    This function should only be called on startup and not on every operation.

    In many cases, it is not necessary to register the client. For example,
    you can create a KMS AEAD with
    kms_aead = gcpkms.GcpKmsClient(key_uri, credentials_path).get_aead(key_uri)
    and then use it to encrypt a keyset with KeysetHandle.write, or to create
    an envelope AEAD using aead.KmsEnvelopeAead.

    Args:
        key_uri: Optional key URI. If set, the registered client will only
          handle that key URI. If not set, then the client will handle all AWS
          KMS key URIs.
        credentials_path: Optional path to the credentials file. If it is not
          set, the default credentials are used.
    """
    tink.register_kms_client(GcpKmsClient(key_uri, credentials_path))
