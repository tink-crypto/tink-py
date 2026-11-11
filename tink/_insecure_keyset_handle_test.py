# Copyright 2023 Google LLC
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

"""Tests for _insecure_keyset_handle."""

from absl.testing import absltest

import tink
from tink import _insecure_keyset_handle
from tink import _monitoring
from tink import aead
from tink import core
from tink import secret_key_access
from tink import tink_config
from tink.testing import fake_key_usage_monitor


def setUpModule():
  tink_config.register()


class InvalidKeyAccess(core.KeyAccess):
  pass


class _RecordingKeyUsageMonitorFactory:
  """Key usage monitor factory that records the monitoring contexts."""

  def __init__(self):
    self.contexts: list[_monitoring.MonitoringContext] = []

  def __call__(
      self, context: _monitoring.MonitoringContext
  ) -> _monitoring.KeyUsageMonitor:
    self.contexts.append(context)
    return fake_key_usage_monitor.FakeKeyUsageMonitor()


class InsecureKeysetHandleTest(absltest.TestCase):

  def _register_key_usage_monitor_factory(
      self,
  ) -> _RecordingKeyUsageMonitorFactory:
    factory = _RecordingKeyUsageMonitorFactory()
    _monitoring.register_key_usage_monitor_factory(factory)
    # Restores the default: no registered factory.
    self.addCleanup(
        _monitoring.register_key_usage_monitor_factory,
        None,  # pyrefly: ignore[bad-argument-type]
    )
    return factory

  def _assert_contexts_have_annotations(
      self,
      factory: _RecordingKeyUsageMonitorFactory,
      expected_annotations: dict[str, str] | None,
  ):
    self.assertNotEmpty(factory.contexts)
    for context in factory.contexts:
      self.assertEqual(
          context.get_keyset_info().get_annotations(), expected_annotations
      )

  def test_from_to_proto_keyset(self):
    keyset_handle = tink.new_keyset_handle(aead.aead_key_templates.AES128_GCM)
    proto_keyset = _insecure_keyset_handle.to_proto_keyset(
        keyset_handle, secret_key_access.TOKEN
    )
    keyset_handle2 = _insecure_keyset_handle.from_proto_keyset(
        proto_keyset, secret_key_access.TOKEN
    )

    # check that keyset_handle and keyset_handle2 are the same.
    plaintext = b'plaintext'
    associated_data = b'associated_data'
    primitive1 = keyset_handle.primitive(aead.Aead)
    ciphertext = primitive1.encrypt(plaintext, associated_data)
    primitive2 = keyset_handle2.primitive(aead.Aead)
    self.assertEqual(primitive2.decrypt(ciphertext, associated_data), plaintext)

    # check that they fail without secret_key_access.TOKEN
    with self.assertRaises(core.TinkError):
      _insecure_keyset_handle.to_proto_keyset(keyset_handle, InvalidKeyAccess())
    with self.assertRaises(core.TinkError):
      _insecure_keyset_handle.from_proto_keyset(
          proto_keyset, InvalidKeyAccess()
      )

  def test_from_proto_keyset_with_annotations(self):
    keyset_handle = tink.new_keyset_handle(aead.aead_key_templates.AES128_GCM)
    plaintext = b'plaintext'
    associated_data = b'associated_data'
    # Encrypts before registering the factory, so that the factory only sees
    # the primitive of the annotated handle.
    ciphertext = keyset_handle.primitive(aead.Aead).encrypt(
        plaintext, associated_data
    )
    proto_keyset = _insecure_keyset_handle.to_proto_keyset(
        keyset_handle, secret_key_access.TOKEN
    )
    factory = self._register_key_usage_monitor_factory()

    annotated_handle = _insecure_keyset_handle.from_proto_keyset(
        proto_keyset,
        secret_key_access.TOKEN,
        {'annotation_key': 'annotation_value'},
    )
    primitive = annotated_handle.primitive(aead.Aead)

    self.assertEqual(primitive.decrypt(ciphertext, associated_data), plaintext)
    self._assert_contexts_have_annotations(
        factory, {'annotation_key': 'annotation_value'}
    )

  def test_from_proto_keyset_copies_annotations(self):
    proto_keyset = _insecure_keyset_handle.to_proto_keyset(
        tink.new_keyset_handle(aead.aead_key_templates.AES128_GCM),
        secret_key_access.TOKEN,
    )
    factory = self._register_key_usage_monitor_factory()
    annotations = {'annotation_key': 'annotation_value'}
    annotated_handle = _insecure_keyset_handle.from_proto_keyset(
        proto_keyset, secret_key_access.TOKEN, annotations
    )

    annotations['annotation_key'] = 'changed_value'
    annotated_handle.primitive(aead.Aead)

    self._assert_contexts_have_annotations(
        factory, {'annotation_key': 'annotation_value'}
    )

  def test_from_proto_keyset_without_annotations(self):
    proto_keyset = _insecure_keyset_handle.to_proto_keyset(
        tink.new_keyset_handle(aead.aead_key_templates.AES128_GCM),
        secret_key_access.TOKEN,
    )
    factory = self._register_key_usage_monitor_factory()
    handle = _insecure_keyset_handle.from_proto_keyset(
        proto_keyset, secret_key_access.TOKEN
    )

    handle.primitive(aead.Aead)

    self._assert_contexts_have_annotations(factory, None)


if __name__ == '__main__':
  absltest.main()
