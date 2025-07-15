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

"""Basic interface for wrapping a primitive."""

import abc
from typing import Generic, Optional, Type, TypeVar

from tink import _monitoring
from tink.core import _primitive_set


B = TypeVar('B')
P = TypeVar('P')


class PrimitiveWrapper(Generic[B, P], metaclass=abc.ABCMeta):
  """Basic interface for wrapping a primitive.

  A PrimitiveSet can be wrapped by a single primitive in order to fulfill a
  cryptographic task. This is done by the PrimitiveWrapper. Whenever a new
  primitive type is added to Tink, the user should define a new PrimitiveWrapper
  and register it by calling registry.registerPrimitiveWrapper().

  The primitive of type B is wrapped into a primitive of type P. In most cases,
  B and P are the same.
  """

  def __init__(self, annotations: Optional[_monitoring.Annotations] = None):
    self._annotations = annotations

  @abc.abstractmethod
  def wrap(self, pset: _primitive_set.PrimitiveSet) -> P:
    """Wraps a PrimitiveSet and returns a single primitive instance."""
    raise NotImplementedError()

  @abc.abstractmethod
  def primitive_class(self) -> Type[P]:
    """Returns the class of the primitive produced by the wrapper."""
    raise NotImplementedError()

  def input_primitive_class(self) -> Type[B]:
    """Returns the class of the primitive that gets wrapped."""
    raise NotImplementedError()

  def _wrap_with_monitoring_info(
      self,
      pset: _primitive_set.PrimitiveSet,
      monitoring_keyset_info: _monitoring.MonitoringKeySetInfo,
  ) -> P:
    """Same as `wrap`, but passes along monitoring annotations.

       By default it does nothing more than `wrap`. Subclasses can override
    this method to handle monitoring annotations.

    Args:
      pset: The PrimitiveSet to wrap.
      monitoring_keyset_info: The monitoring information to pass along.

    Returns:
      The wrapped primitive.
    """
    if monitoring_keyset_info.get_annotations():
      raise NotImplementedError(
          'Support for monitoring is not implemented for this'
          ' primitive'
      )
    # Monitoring is optional and thus ignored by default.
    del monitoring_keyset_info
    return self.wrap(pset)
