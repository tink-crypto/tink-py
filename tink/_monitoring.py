# Copyright 2025 Google LLC
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

"""Monitoring for Tink.

Defines entities related to monitoring of key usage.
"""

import abc
from typing import Callable, Optional

_registered_key_usage_monitor_factory = None


class KeyUsageMonitor(metaclass=abc.ABCMeta):
  """Interface for monitoring the usage of keys.

  This interface is used by all Tink primitives to report key usage.
  """

  @abc.abstractmethod
  def log(self, key_id: int, num_bytes_as_input: int):
    """Logs a successful use of `key_id` on an input of `num_bytes_as_input`.

    Tink primitive wrappers call this method when they successfully used a key
    to
    carry out a primitive method, e.g. Aead.encrypt(). As a consequence,
    subclasses should be mindful on the amount of work
    performed by this method, as this will be called on each cryptographic
    operation. Implementations are responsible to add
    context to identify, e.g., the primitive and the API function.

    Args:
      key_id: The key ID of the used key.
      num_bytes_as_input: The size of the input used for the cryptographic
        operation.
    """
    pass

  @abc.abstractmethod
  def log_failure(self):
    """Logs a failure of a cryptographic operation.

    Tink calls this method when a cryptographic operation
    fails, e.g. no key could be found to decrypt a ciphertext. In this
    case the failure is not associated with a specific key, therefore this
    method has no arguments. The MonitoringClient implementation is responsible
    to add context to identify where the failure comes from.
    """
    pass


def register_key_usage_monitor_factory(f: Callable[[], KeyUsageMonitor]):
  """Registers a factory for creating KeyUsageMonitor objects.

  The factory will be called in the `wrap` method of the primitive wrappers
  and passed to the respective primitives to be used when using the keys.

  Args:
    f: A factory function that returns a KeyUsageMonitor object. Called every
      time the monitor is requested with `get_monitor_or_none`.
  """
  global _registered_key_usage_monitor_factory
  _registered_key_usage_monitor_factory = f


def get_key_usage_monitor_or_none() -> Optional[KeyUsageMonitor]:
  """Returns a new instance of a KeyUsageMonitor.

  The instance is created using the registered factory. If no factory has been
  registered, None is returned.
  """
  return (
      _registered_key_usage_monitor_factory()
      if _registered_key_usage_monitor_factory is not None
      else None
  )
