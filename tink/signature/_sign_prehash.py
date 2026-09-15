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

"""Interface for SignPrehash."""

import abc

from tink import core
from tink.cc.pybind import tink_bindings


class SignPrehash(metaclass=abc.ABCMeta):
  """Interface for prehash signing."""

  @abc.abstractmethod
  def sign(self, prehash: bytes) -> bytes:
    """Computes the signature for a prehash.

    Args:
      prehash: bytes, the prehash data.

    Returns:
      The signature as bytes.
    """
    raise NotImplementedError()


class SignPrehashCcToPyWrapper(SignPrehash):
  """Transforms C++ SignPrehash into a Python primitive."""

  def __init__(self, cc_primitive: tink_bindings.SignPrehash):
    self._sign_prehash = cc_primitive

  @core.use_tink_errors
  def sign(self, prehash: bytes) -> bytes:
    return self._sign_prehash.sign(prehash)
