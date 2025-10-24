# Copyright 2021 Google LLC
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
# [START encrypted-keyset-example]
"""A command-line utility for generating, encrypting and storing keysets."""

from absl import app
from absl import flags
from absl import logging

import tink
from tink import aead
from tink.integration import gcpkms


FLAGS = flags.FLAGS

flags.DEFINE_enum('mode', None, ['generate', 'encrypt', 'decrypt'],
                  'The operation to perform.')
flags.DEFINE_string('keyset_path', None,
                    'Path to the keyset used for encryption.')
flags.DEFINE_string('kek_uri', None,
                    'The Cloud KMS URI of the key encryption key.')
flags.DEFINE_string('gcp_credential_path', None,
                    'Path to the GCP credentials JSON file.')
flags.DEFINE_string('input_path', None, 'Path to the input file.')
flags.DEFINE_string('output_path', None, 'Path to the output file.')
flags.DEFINE_string('associated_data', None,
                    'Optional associated data to use with the '
                    'encryption operation.')


def main(argv):
  del argv  # Unused.

  associated_data = b'' if not FLAGS.associated_data else bytes(
      FLAGS.associated_data, 'utf-8')

  # Initialise Tink
  aead.register()

  try:
    # Read the GCP credentials and setup client
    client = gcpkms.GcpKmsClient(FLAGS.kek_uri, FLAGS.gcp_credential_path)
  except tink.TinkError as e:
    logging.exception('Error creating GCP KMS client: %s', e)
    return 1

  # Create envelope AEAD primitive using AES128 GCM for encrypting the data
  try:
    remote_aead = client.get_aead(FLAGS.kek_uri)
  except tink.TinkError as e:
    logging.exception('Error creating primitive: %s', e)
    return 1

  if FLAGS.mode == 'generate':
    # [START generate-a-new-keyset]
    # Generate a new keyset
    try:
      key_template = aead.aead_key_templates.AES128_GCM
      keyset_handle = tink.new_keyset_handle(key_template)
    except tink.TinkError as e:
      logging.exception('Error creating primitive: %s', e)
      return 1
    # [END generate-a-new-keyset]

    # [START encrypt-a-keyset]
    # Encrypt the keyset_handle with the remote key-encryption key (KEK)
    with open(FLAGS.keyset_path, 'wt') as keyset_file:
      try:
        keyset_encryption_associated_data = 'encrypted keyset example'
        serialized_encrypted_keyset = (
            tink.json_proto_keyset_format.serialize_encrypted(
                keyset_handle, remote_aead, keyset_encryption_associated_data
            )
        )
        keyset_file.write(serialized_encrypted_keyset)
      except tink.TinkError as e:
        logging.exception('Error writing key: %s', e)
        return 1
    return 0
    # [END encrypt-a-keyset]

  # Use the keyset to encrypt/decrypt data

  # Read the encrypted keyset into a keyset_handle
  with open(FLAGS.keyset_path, 'rt') as keyset_file:
    try:
      serialized_encrypted_keyset = keyset_file.read()
      keyset_encryption_associated_data = 'encrypted keyset example'
      keyset_handle = tink.json_proto_keyset_format.parse_encrypted(
          serialized_encrypted_keyset,
          remote_aead,
          keyset_encryption_associated_data,
      )
    except tink.TinkError as e:
      logging.exception('Error reading key: %s', e)
      return 1

  # Get the primitive
  try:
    cipher = keyset_handle.primitive(aead.Aead)
  except tink.TinkError as e:
    logging.exception('Error creating primitive: %s', e)
    return 1

  with open(FLAGS.input_path, 'rb') as input_file:
    input_data = input_file.read()
    if FLAGS.mode == 'decrypt':
      output_data = cipher.decrypt(input_data, associated_data)
    elif FLAGS.mode == 'encrypt':
      output_data = cipher.encrypt(input_data, associated_data)
    else:
      logging.error(
          'Unsupported mode %s. Please choose "encrypt" or "decrypt".',
          FLAGS.mode,
      )
      return 1

    with open(FLAGS.output_path, 'wb') as output_file:
      output_file.write(output_data)


if __name__ == '__main__':
  flags.mark_flags_as_required([
      'mode', 'keyset_path', 'kek_uri', 'gcp_credential_path'])
  app.run(main)
# [END encrypted-keyset-example]
