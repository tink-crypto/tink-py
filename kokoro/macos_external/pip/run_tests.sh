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


# The user may specify TINK_BASE_DIR for setting a local copy of Tink to use
# when running the script locally.

set -euo pipefail

BAZEL_CMD="bazel"
if command -v "bazelisk" &> /dev/null; then
  BAZEL_CMD="bazelisk"
fi
readonly BAZEL_CMD

# If we are running on Kokoro cd into the repository.
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_py"
fi

: "${TINK_BASE_DIR:=$(cd .. && pwd)}"

# Check for dependencies in TINK_BASE_DIR. Any that aren't present will be
# downloaded.
readonly GITHUB_ORG="https://github.com/tink-crypto"
./kokoro/testutils/fetch_git_repo_if_not_present.sh "${TINK_BASE_DIR}" \
  "${GITHUB_ORG}/tink-cc" "${GITHUB_ORG}/tink-cc-awskms" \
  "${GITHUB_ORG}/tink-cc-gcpkms"

./kokoro/testutils/copy_credentials.sh "testdata" "all"
# Sourcing required to update callers environment.
source ./kokoro/testutils/install_protoc.sh
source ./kokoro/testutils/install_tink_via_pip.sh "$(pwd)"

# Get root certificates for gRPC
curl -OLsS https://raw.githubusercontent.com/grpc/grpc/master/etc/roots.pem
export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$(pwd)/roots.pem"

# testing/helper.py will look for testdata in TINK_PYTHON_ROOT_PATH/testdata.
export TINK_PYTHON_ROOT_PATH="$(pwd)"
# Run Python tests directly so the package is used.
# We exclude tests in tink/cc/pybind: they are implementation details and may
# depend on a testonly shared object.
find tink/ -not -path "*cc/pybind*" -type f -name "*_test.py" -print0 \
  | xargs -0 -n1 python3
