# Copyright 2022 Google LLC
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
"""Tests for exception (non-)propagation in Pybind11PythonFileObjectAdapter."""

import gc
import io
import sys

from absl.testing import absltest
from absl.testing.absltest import mock

import tink
from tink import streaming_aead


def setUpModule():
  streaming_aead.register()


def get_primitive() -> streaming_aead.StreamingAead:
  key_template = streaming_aead.streaming_aead_key_templates.AES128_GCM_HKDF_4KB
  keyset_handle = tink.new_keyset_handle(key_template)
  primitive = keyset_handle.primitive(streaming_aead.StreamingAead)
  return primitive


class BytesIOThatThrowsExceptionsOnReadWrite(io.BytesIO):

  def write(self, data):
    raise tink.TinkError('Called write!')

  def read(self, num):  # pyrefly: ignore[bad-override]
    raise tink.TinkError('Called read!')

  def close(self):
    pass


class BytesIOThatThrowsExceptionsOnClose(io.BytesIO):

  def write(self, data):
    return len(data)

  def read(self, _):  # pyrefly: ignore[bad-override]
    return b''

  def close(self):
    super().close()
    raise tink.TinkError('Called close!')


class Pybind11PythonFileObjectAdaterTest(absltest.TestCase):

  # These tests call close() directly instead of using the `with` statement,
  # to check the exception that close() raises.
  def test_write_throws(self):
    streaming_aead_primitive = get_primitive()

    with mock.patch.object(sys, 'unraisablehook') as unraisablehook:
      ciphertext_destination = BytesIOThatThrowsExceptionsOnReadWrite()
      enc_stream = streaming_aead_primitive.new_encrypting_stream(
          ciphertext_destination, b'associated_data')
      # The exception is thrown but swallowed on the way.
      _ = enc_stream.write(b'plaintext')
      # The exception is thrown and is not swallowed.
      self.assertRaises(tink.TinkError, enc_stream.close)
      # The failed close() still closes the stream, so that its finalizer does
      # not try again.
      self.assertTrue(enc_stream.closed)
      del enc_stream, ciphertext_destination
      gc.collect()
    unraisablehook.assert_not_called()

  def test_read_throws(self):
    streaming_aead_primitive = get_primitive()

    ciphertext_source = BytesIOThatThrowsExceptionsOnReadWrite()
    dec_stream = streaming_aead_primitive.new_decrypting_stream(
        ciphertext_source, b'associated_data')
    self.assertRaises(tink.TinkError, dec_stream.read)
    dec_stream.close()

  def test_close_throws(self):
    streaming_aead_primitive = get_primitive()

    with mock.patch.object(sys, 'unraisablehook') as unraisablehook:
      ciphertext_destination = BytesIOThatThrowsExceptionsOnClose()
      enc_stream = streaming_aead_primitive.new_encrypting_stream(
          ciphertext_destination, b'associated_data')
      self.assertRaises(tink.TinkError, enc_stream.close)
      # The failed close() still closes the stream, so that its finalizer does
      # not try again.
      self.assertTrue(enc_stream.closed)
      del enc_stream, ciphertext_destination
      gc.collect()
    unraisablehook.assert_not_called()


if __name__ == '__main__':
  absltest.main()
