#!/bin/bash
# Copyright 2022 Google LLC
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
################################################################################
# Generated with openssl rand -hex 10
echo "==========================================================================="
echo "Tink Script ID: 1b121d810c623b0c9cc8 (to quickly find the script from logs)"
echo "==========================================================================="

set -euox pipefail

# When running under Kokoro, change into git/tink_py (or github/tink_py)
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  cd "${KOKORO_ARTIFACTS_DIR}"
  cd git*/tink_py
fi

./kokoro/testutils/copy_credentials.sh "testdata" "all"
./kokoro/testutils/copy_credentials.sh "examples/testdata" "gcp"

CACHE_FLAGS=()
if [[ -n "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET:-}" ]]; then
  cp "${TINK_REMOTE_BAZEL_CACHE_SERVICE_KEY}" ./cache_key
  CACHE_FLAGS+=("--remote_cache=https://storage.googleapis.com/${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET}")
  CACHE_FLAGS+=("--google_credentials=$(realpath ./cache_key)")
fi
readonly CACHE_FLAGS

echo "---------- BUILDING MAIN ($(date))"
bazelisk build "${CACHE_FLAGS[@]}" -- ...
echo "---------- TESTING MAIN ($(date))"
bazelisk test "${CACHE_FLAGS[@]}" -- ...

cd examples
echo "---------- BUILDING EXAMPLES ($(date))"
bazelisk build "${CACHE_FLAGS[@]}" -- ...
echo "---------- TESTING EXAMPLES ($(date))"
bazelisk test "${CACHE_FLAGS[@]}" -- ...
