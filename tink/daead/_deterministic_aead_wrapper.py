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

"""Deterministic AEAD wrapper."""

from typing import Optional, Type

from tink import _monitoring
from tink import core
from tink.daead import _deterministic_aead


class _WrappedDeterministicAead(_deterministic_aead.DeterministicAead):
  """Implements DeterministicAead for a set of DeterministicAead primitives."""

  def __init__(
      self,
      pset: core.PrimitiveSet,
      monitor: Optional[_monitoring.KeyUsageMonitor] = None,
  ):
    self._primitive_set = pset
    self._monitor = monitor

  def encrypt_deterministically(
      self, plaintext: bytes, associated_data: bytes
  ) -> bytes:
    primary = self._primitive_set.primary()
    result = primary.identifier + primary.primitive.encrypt_deterministically(
        plaintext, associated_data
    )

    if self._monitor:
      self._monitor.log(primary.key_id, len(plaintext))

    return result

  def decrypt_deterministically(
      self, ciphertext: bytes, associated_data: bytes
  ) -> bytes:
    if len(ciphertext) > core.crypto_format.NON_RAW_PREFIX_SIZE:
      prefix = ciphertext[: core.crypto_format.NON_RAW_PREFIX_SIZE]
      ciphertext_no_prefix = ciphertext[
          core.crypto_format.NON_RAW_PREFIX_SIZE :
      ]
      for entry in self._primitive_set.primitive_from_identifier(prefix):
        try:
          result = entry.primitive.decrypt_deterministically(
              ciphertext_no_prefix, associated_data
          )

          if self._monitor:
            self._monitor.log(entry.key_id, len(ciphertext_no_prefix))

          return result
        except core.TinkError:
          pass
    # Let's try all RAW keys.
    for entry in self._primitive_set.raw_primitives():
      try:
        result = entry.primitive.decrypt_deterministically(
            ciphertext, associated_data
        )

        if self._monitor:
          self._monitor.log(entry.key_id, len(ciphertext))

        return result
      except core.TinkError:
        pass

    # nothing works.
    if self._monitor:
      self._monitor.log_failure()

    raise core.TinkError('Decryption failed.')


class DeterministicAeadWrapper(
    core.PrimitiveWrapper[
        _deterministic_aead.DeterministicAead,
        _deterministic_aead.DeterministicAead,
    ]
):
  """DeterministicAeadWrapper is a PrimitiveWrapper for DeterministicAead.

  The created primitive works with a keyset (rather than a single key). To
  encrypt a plaintext, it uses the primary key in the keyset, and prepends to
  the ciphertext a certain prefix associated with the primary key. To decrypt,
  the primitive uses the prefix of the ciphertext to efficiently select the
  right key in the set. If the keys associated with the prefix do not work, the
  primitive tries all keys with OutputPrefixType RAW.
  """

  def wrap(
      self, pset: core.PrimitiveSet
  ) -> _deterministic_aead.DeterministicAead:
    return _WrappedDeterministicAead(pset)

  def primitive_class(self) -> Type[_deterministic_aead.DeterministicAead]:
    return _deterministic_aead.DeterministicAead

  def input_primitive_class(
      self,
  ) -> Type[_deterministic_aead.DeterministicAead]:
    return _deterministic_aead.DeterministicAead

  def _wrap_with_annotations(
      self,
      pset: core.PrimitiveSet,
      annotations: Optional[_monitoring.Annotations],
  ) -> _deterministic_aead.DeterministicAead:
    key_usage_monitor = _monitoring.get_key_usage_monitor_or_none(
        annotations
    )
    return _WrappedDeterministicAead(pset, key_usage_monitor)
