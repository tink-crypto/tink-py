#!/bin/bash
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
################################################################################

# Generated with openssl rand -hex 10
echo "==========================================================================="
echo "Tink Script ID: a04907578326ffc15fe7 (to quickly find the script from logs)"
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
  # Avoid downloading cached intermediate/top-level build outputs unless needed
  # by a local action.
  CACHE_FLAGS+=("--remote_download_minimal")
fi
readonly CACHE_FLAGS

# --nobuild_tests_only ensures all non-test targets in '...' are built too.
echo "---------- BUILDING AND TESTING MAIN ($(date))"
bazelisk test --nobuild_tests_only ${CACHE_FLAGS[@]:+"${CACHE_FLAGS[@]}"} -- ...

cd examples
echo "---------- BUILDING AND TESTING EXAMPLES ($(date))"
bazelisk test --nobuild_tests_only ${CACHE_FLAGS[@]:+"${CACHE_FLAGS[@]}"} -- ...


echo "---------- KMS Specific tests"
TARGETS=$(bazel query 'attr(tags, requires_kms, ...) except attr(tags, tests_pip_install_tink, ...)')
echo "${TARGETS}"

echo "---------- BUILDING AND TESTING KMS Specific tests ($(date))"
bazelisk test --nobuild_tests_only ${CACHE_FLAGS[@]:+"${CACHE_FLAGS[@]}"} -- $TARGETS
