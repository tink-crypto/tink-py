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

from absl.testing import absltest

from tink.proto import tink_pb2
from tink import _monitoring
from tink.testing import fake_key_usage_monitor


def _new_fake_key_usage_monitor(
    context: _monitoring.MonitoringContext,
) -> _monitoring.KeyUsageMonitor:
  del context  # Unused.
  return fake_key_usage_monitor.FakeKeyUsageMonitor()


def _new_no_key_usage_monitor(
    context: _monitoring.MonitoringContext,
) -> _monitoring.KeyUsageMonitor | None:
  del context  # Unused.
  return None


class MonitoringTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    # Restores the default: no registered factory.
    self.addCleanup(
        _monitoring.register_key_usage_monitor_factory,
        None,  # pyrefly: ignore[bad-argument-type]
    )

  def test_get_key_usage_monitor_factory_without_registered_factory(self):
    self.assertIsNone(_monitoring.get_key_usage_monitor_factory())

  def test_get_key_usage_monitor_factory_returns_registered_factory(self):
    _monitoring.register_key_usage_monitor_factory(_new_fake_key_usage_monitor)

    self.assertIs(
        _monitoring.get_key_usage_monitor_factory(), _new_fake_key_usage_monitor
    )

  def test_get_key_usage_monitor_or_none_when_factory_returns_none(self):
    _monitoring.register_key_usage_monitor_factory(_new_no_key_usage_monitor)
    context = _monitoring.MonitoringContext(
        primitive='aead',
        api_function='encrypt',
        keyset_info=_monitoring.MonitoringKeySetInfo(
            {'key': 'value'}, tink_pb2.KeysetInfo()
        ),
    )

    self.assertIsNone(_monitoring.get_key_usage_monitor_or_none(context))


if __name__ == '__main__':
  absltest.main()
