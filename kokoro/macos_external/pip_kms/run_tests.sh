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
# Builds and installs tink-py via PIP and run tink-py and examples tests.

# Generated with openssl rand -hex 10
echo "==========================================================================="
echo "Tink Script ID: 8a1dad4b2664a07b4976 (to quickly find the script from logs)"
echo "==========================================================================="

set -euox pipefail

# If we are running on Kokoro cd into the repository.
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  readonly TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_py"
fi

# Sourcing required to update callers environment.
source ./kokoro/testutils/install_protoc.sh "30.2"

./kokoro/testutils/install_tink_via_pip.sh -a "$(pwd)"
source ./kokoro/testutils/install_vault.sh
source ./kokoro/testutils/run_hcvault_test_server.sh
vault write -f transit/keys/key-1

CACHE_FLAGS=()
if [[ -n "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET:-}" ]]; then
  cp "${TINK_REMOTE_BAZEL_CACHE_SERVICE_KEY}" ./cache_key
  CACHE_FLAGS+=("--remote_cache=https://storage.googleapis.com/${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET}")
  CACHE_FLAGS+=("--google_credentials=$(realpath ./cache_key)")
fi
readonly CACHE_FLAGS

# testing/helper.py will look for testdata in TINK_PYTHON_ROOT_PATH/testdata.
export TINK_PYTHON_ROOT_PATH="$(pwd)"

./kokoro/testutils/copy_credentials.sh "testdata" "all"
./kokoro/testutils/copy_credentials.sh "examples/testdata" "gcp"

echo "---------- RUNNING TEST WITH PYTHON ($(date))"
find tink/ -type f -name "*_test.py" -print0 | xargs -t -0 -n1 python3

cd examples

echo "--------- tests_pip_install_tink tests"
TARGETS=$(bazel query 'attr(tags, tests_pip_install_tink, ...) except attr(tags, requires_kms, ...)')
echo "${TARGETS}"

echo "---------- BUILDING KMS Specific tests ($(date))"
bazelisk build "${CACHE_FLAGS[@]}" -- $TARGETS
echo "---------- TESTING KMS Specific tests ($(date))"
bazelisk test "${CACHE_FLAGS[@]}" -- $TARGETS
