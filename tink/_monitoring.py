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
from typing import Callable, Dict, Optional

from tink.proto import tink_pb2


Annotations = Dict[str, str]


class MonitoringKeySetInfo:
  """Immutable representation of a KeySet in a certain point in time for the purpose of monitoring operations involving cryptographic keys."""

  def __init__(
      self,
      annotations: Optional[Annotations],
      keyset_info: tink_pb2.KeysetInfo,
  ):
    self._annotations = annotations
    self._keyset_info = keyset_info

  def get_annotations(self) -> Optional[Annotations]:
    return self._annotations

  def get_keyset_info(self) -> tink_pb2.KeysetInfo:
    return self._keyset_info


class MonitoringContext:
  """Context for monitoring events, consisting of the primitive, API used and info on the keyset."""

  def __init__(
      self,
      primitive: str,
      api_function: str,
      keyset_info: MonitoringKeySetInfo,
  ):
    self._primitive = primitive
    self._api_function = api_function
    self._keyset_info = keyset_info

  def get_primitive(self) -> str:
    return self._primitive

  def get_api_function(self) -> str:
    return self._api_function

  def get_keyset_info(self) -> MonitoringKeySetInfo:
    return self._keyset_info


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


_registered_key_usage_monitor_factory: Callable[
    [MonitoringContext], KeyUsageMonitor
] = None


def register_key_usage_monitor_factory(
    f: Callable[[MonitoringContext], KeyUsageMonitor],
):
  """Registers a factory for creating KeyUsageMonitor objects.

  The factory will be called in the `wrap` method of the primitive wrappers
  and passed to the respective primitives to be used when using the keys.

  Args:
    f: A factory function that returns a KeyUsageMonitor object. Called every
      time the monitor is requested with `get_monitor_or_none`.
  """
  global _registered_key_usage_monitor_factory
  _registered_key_usage_monitor_factory = f


def get_key_usage_monitor_or_none(
    monitoring_context: MonitoringContext,
) -> Optional[KeyUsageMonitor]:
  """Returns a new instance of a KeyUsageMonitor or None.

  The instance is created using the registered factory, passing keyset_info
  along. None is returned if there is no registered factory.

  Args:
    monitoring_context: Context object with all monitoring-related information.

  Returns:
    A new instance of a KeyUsageMonitor or None.
  """
  return (
      _registered_key_usage_monitor_factory(monitoring_context)
      if _registered_key_usage_monitor_factory is not None
      else None
  )
