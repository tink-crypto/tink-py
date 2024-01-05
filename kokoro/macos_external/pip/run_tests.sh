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

# Make sure we use the latest Python 3.11.
eval "$(pyenv init -)"
pyenv install "3.11"
pyenv global "3.11"

# Sourcing required to update callers environment.
source ./kokoro/testutils/install_protoc.sh "25.1"

# testing/helper.py will look for testdata in TINK_PYTHON_ROOT_PATH/testdata.
export TINK_PYTHON_ROOT_PATH="$(pwd)"
TEST_EXCLUDE=( -not -path "*cc/pybind*" )
if [[ "${TEST_WITH_KMS}" == "true" ]]; then
  ./kokoro/testutils/install_tink_via_pip.sh -a "$(pwd)"
  ./kokoro/testutils/copy_credentials.sh "testdata" "all"
else
  ./kokoro/testutils/install_tink_via_pip.sh "$(pwd)"
  TEST_EXCLUDE+=( -not -path "*integration/*" )
fi
readonly TEST_EXCLUDE
find tink/ "${TEST_EXCLUDE}" -type f -name "*_test.py" -print0 \
  | xargs -0 -n1 python3

# Install requirements for examples.
python3 -m pip install --require-hashes --no-deps -r examples/requirements.txt
if [[ "${TEST_WITH_KMS}" == "true" ]]; then
  # Get root certificates for gRPC.
  curl -OLsS https://raw.githubusercontent.com/grpc/grpc/master/etc/roots.pem
  export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$(pwd)/roots.pem"
  ./kokoro/testutils/copy_credentials.sh "examples/testdata" "gcp"
  # All *test_package targets, including manual ones.
  TARGETS="$(cd examples && "${BAZEL_CMD}" query 'filter(.*test_package, ...)')"
else
  # All non-manual *test_package targets.
  TARGETS="$(cd examples && "${BAZEL_CMD}" query \
    'filter(.*test_package, ...) except attr(tags, manual, ...)')"
fi
readonly TARGETS

IFS=' ' read -a TARGETS_ARRAY <<< "$(tr '\n' ' ' <<< "${TARGETS}")"
readonly TARGETS_ARRAY
./kokoro/testutils/run_bazel_tests.sh -m "examples" "${TARGETS_ARRAY[@]}"
