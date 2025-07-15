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

"""HybridDecrypt wrapper."""

from typing import Optional, Type

from tink import _monitoring
from tink import core
from tink.hybrid import _hybrid_decrypt
from tink.hybrid import _hybrid_encrypt


class _WrappedHybridDecrypt(_hybrid_decrypt.HybridDecrypt):
  """Implements HybridDecrypt for a set of HybridDecrypt primitives."""

  def __init__(
      self,
      pset: core.PrimitiveSet,
      monitor: Optional[_monitoring.KeyUsageMonitor] = None,
  ):
    self._primitive_set = pset
    self._monitor = monitor

  def decrypt(self, ciphertext: bytes, context_info: bytes) -> bytes:
    if len(ciphertext) > core.crypto_format.NON_RAW_PREFIX_SIZE:
      prefix = ciphertext[: core.crypto_format.NON_RAW_PREFIX_SIZE]
      ciphertext_no_prefix = ciphertext[
          core.crypto_format.NON_RAW_PREFIX_SIZE :
      ]
      for entry in self._primitive_set.primitive_from_identifier(prefix):
        try:
          result = entry.primitive.decrypt(ciphertext_no_prefix, context_info)
          if self._monitor:
            self._monitor.log(entry.key_id, len(ciphertext_no_prefix))

          return result
        except core.TinkError:
          pass
    # Let's try all RAW keys.
    for entry in self._primitive_set.raw_primitives():
      try:
        result = entry.primitive.decrypt(ciphertext, context_info)

        if self._monitor:
          self._monitor.log(entry.key_id, len(ciphertext))

        return result
      except core.TinkError:
        pass

    # nothing works.
    if self._monitor:
      self._monitor.log_failure()

    raise core.TinkError('Decryption failed.')


class HybridDecryptWrapper(
    core.PrimitiveWrapper[
        _hybrid_decrypt.HybridDecrypt, _hybrid_decrypt.HybridDecrypt
    ]
):
  """HybridDecryptWrapper is the PrimitiveWrapper for HybridDecrypt.

  The returned primitive works with a keyset (rather than a single key). To
  decrypt, the primitive uses the prefix of the ciphertext to efficiently select
  the right key in the set. If the keys associated with the prefix do not work,
  the primitive tries all keys with OutputPrefixType RAW.
  """

  def wrap(self, pset: core.PrimitiveSet) -> _hybrid_decrypt.HybridDecrypt:
    return _WrappedHybridDecrypt(pset)

  def primitive_class(self) -> Type[_hybrid_decrypt.HybridDecrypt]:
    return _hybrid_decrypt.HybridDecrypt

  def input_primitive_class(self) -> Type[_hybrid_decrypt.HybridDecrypt]:
    return _hybrid_decrypt.HybridDecrypt

  def _wrap_with_monitoring_info(
      self,
      pset: core.PrimitiveSet,
      monitoring_keyset_info: _monitoring.MonitoringKeySetInfo,
  ) -> _hybrid_decrypt.HybridDecrypt:
    key_usage_monitor = _monitoring.get_key_usage_monitor_or_none(
        _monitoring.MonitoringContext(
            primitive='hybrid_decrypt',
            api_function='decrypt',
            keyset_info=monitoring_keyset_info,
        )
    )
    return _WrappedHybridDecrypt(pset, key_usage_monitor)


class _WrappedHybridEncrypt(_hybrid_encrypt.HybridEncrypt):
  """Implements HybridEncrypt for a set of HybridEncrypt primitives."""

  def __init__(
      self,
      pset: core.PrimitiveSet,
      monitor: Optional[_monitoring.KeyUsageMonitor] = None,
  ):
    self._primitive_set = pset
    self._monitor = monitor

  def encrypt(self, plaintext: bytes, context_info: bytes) -> bytes:
    if not self._primitive_set.primary():
      raise core.TinkError('keyset without primary key')

    primary = self._primitive_set.primary()
    result = primary.identifier + primary.primitive.encrypt(
        plaintext, context_info
    )

    if self._monitor:
      self._monitor.log(primary.key_id, len(plaintext))

    return result


class HybridEncryptWrapper(
    core.PrimitiveWrapper[
        _hybrid_encrypt.HybridEncrypt, _hybrid_encrypt.HybridEncrypt
    ]
):
  """HybridEncryptWrapper is the PrimitiveWrapper for HybridEncrypt.

  The returned primitive works with a keyset (rather than a single key). To
  encrypt a plaintext, it uses the primary key in the keyset, and prepends to
  the ciphertext a certain prefix associated with the primary key.
  """

  def wrap(self, pset: core.PrimitiveSet) -> _hybrid_encrypt.HybridEncrypt:
    return _WrappedHybridEncrypt(pset)

  def primitive_class(self) -> Type[_hybrid_encrypt.HybridEncrypt]:
    return _hybrid_encrypt.HybridEncrypt

  def input_primitive_class(self) -> Type[_hybrid_encrypt.HybridEncrypt]:
    return _hybrid_encrypt.HybridEncrypt

  def _wrap_with_monitoring_info(
      self,
      pset: core.PrimitiveSet,
      monitoring_keyset_info: _monitoring.MonitoringKeySetInfo,
  ) -> _hybrid_encrypt.HybridEncrypt:
    key_usage_monitor = _monitoring.get_key_usage_monitor_or_none(
        _monitoring.MonitoringContext(
            primitive='hybrid_encrypt',
            api_function='encrypt',
            keyset_info=monitoring_keyset_info,
        )
    )
    return _WrappedHybridEncrypt(pset, key_usage_monitor)
