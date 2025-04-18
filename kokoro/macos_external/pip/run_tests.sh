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

# Builds and installs tink-py via PIP and run tink-py and examples tests.
set -euo pipefail

BAZEL_CMD="bazel"
if command -v "bazelisk" &> /dev/null; then
  BAZEL_CMD="bazelisk"
fi
readonly BAZEL_CMD

TEST_WITH_KMS="false"
if [[ "${KOKORO_JOB_NAME:-}" =~ .*/pip_kms/.* ]]; then
  TEST_WITH_KMS="true"
fi
readonly TEST_WITH_KMS

# If we are running on Kokoro cd into the repository.
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  readonly TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_py"
fi

# Make sure we use the latest Python 3.13 available with pyenv.
# The macOS image exports a PYENV_ROOT env variable.
(
  cd "${PYENV_ROOT:-"${HOME}/.pyenv"}"
  git pull
  eval "$(pyenv init -)"
  pyenv install -s "3.13"
  pyenv global "3.13"
)

# Sourcing required to update callers environment.
source ./kokoro/testutils/install_protoc.sh "30.2"

./kokoro/testutils/copy_credentials.sh "testdata" "all"
./kokoro/testutils/copy_credentials.sh "examples/testdata" "gcp"

# Fill in TEST_SCRIPT_ARGS with arguments to pass to the test script.
TEST_SCRIPT_ARGS=()
if [[ "${KOKORO_JOB_NAME:-}" =~ .*/bazel_kms/.* ]]; then
  TEST_SCRIPT_ARGS+=( -k )
fi
if [[ -n "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET:-}" ]]; then
  cp "${TINK_REMOTE_BAZEL_CACHE_SERVICE_KEY}" ./cache_key
  TEST_SCRIPT_ARGS+=(
    -c "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET}/bazel/macos_tink_py"
  )
fi
readonly TEST_SCRIPT_ARGS

./kokoro/gcp_ubuntu/pip/test_script.sh "${TEST_SCRIPT_ARGS[@]}"
