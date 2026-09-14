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

"""Interface for Prehash."""

import abc

from tink import core
from tink.cc.pybind import tink_bindings


class Prehash(metaclass=abc.ABCMeta):
  """Interface for generating precomputed hash values."""

  @abc.abstractmethod
  def compute(self, data: bytes) -> bytes:
    """Computes the prehash for data.

    Args:
      data: bytes, the input data.

    Returns:
      The prehash as bytes.
    """
    raise NotImplementedError()


class PrehashCcToPyWrapper(Prehash):
  """Transforms C++ Prehash into a Python primitive."""

  def __init__(self, cc_primitive: tink_bindings.Prehash):
    self._prehash = cc_primitive

  @core.use_tink_errors
  def compute(self, data: bytes) -> bytes:
    return self._prehash.compute(data)
