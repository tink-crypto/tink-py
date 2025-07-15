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

"""Provides a fake KeyUsageMonitor for testing."""

from typing import List, Tuple

from tink import _monitoring


class FakeKeyUsageMonitor(_monitoring.KeyUsageMonitor):
  """Implementation of KeyUsageMonitor that only records its method calls."""

  def __init__(self):
    self.log_calls: List[Tuple[int, int]] = []
    self.log_failure_calls_count: int = 0

  def log(self, key_id: int, num_bytes_as_input: int) -> None:
    self.log_calls.append((key_id, num_bytes_as_input))

  def log_failure(self) -> None:
    self.log_failure_calls_count += 1
