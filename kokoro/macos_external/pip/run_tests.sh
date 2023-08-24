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
#
# The behavior of this script can be modified using the following optional env
# variables:
#
# - CONTAINER_IMAGE (unset by default): By default when run locally this script
#   executes tests directly on the host. The CONTAINER_IMAGE variable can be set
#   to execute tests in a custom container image for local testing. E.g.:
#
#   CONTAINER_IMAGE="us-docker.pkg.dev/tink-test-infrastructure/tink-ci-images/linux-tink-py-base:latest" \
#     sh ./kokoro/macos_external/pip/run_tests.sh
#
# - USE_LOCAL_TINK_CC ("true" by default): If true, the script  uses a local
#   version of tink_cc located at TINK_BASE_DIR (see below).
#   NOTE: tink_cc is fetched from GitHub if not found.
#
# - TINK_BASE_DIR (../ by default): This is the folder where to look for
#   tink-py and its dependencies. That is ${TINK_BASE_DIR}/tink_py and
#   optionally ${TINK_BASE_DIR}/tink_cc.
set -euo pipefail

BAZEL_CMD="bazel"
if command -v "bazelisk" &> /dev/null; then
  BAZEL_CMD="bazelisk"
fi
readonly BAZEL_CMD

if [[ -z "${USE_LOCAL_TINK_CC:-}" ]]; then
  if [[ "${KOKORO_PARENT_JOB_NAME:-}" =~ tink/github/py/.*_release ]]; then
    USE_LOCAL_TINK_CC="false"
  else
    USE_LOCAL_TINK_CC="true"
  fi
fi
readonly USE_LOCAL_TINK_CC

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
  "${GITHUB_ORG}/tink-cc"

./kokoro/testutils/copy_credentials.sh "testdata" "all"
./kokoro/testutils/copy_credentials.sh "examples/testdata" "gcp"

# Sourcing required to update callers environment.
source ./kokoro/testutils/install_protoc.sh

if [[ "${USE_LOCAL_TINK_CC}" == "true" ]]; then
  sed -i '.bak' 's~# Placeholder for tink-cc override.~\
local_repository(\
    name = "tink_cc",\
    path = "../tink_cc",\
)~' WORKSPACE
fi

./kokoro/testutils/install_tink_via_pip.sh "$(pwd)"

if [[ -f "WORKSPACE.bak" ]]; then
  mv "WORKSPACE.bak" "WORKSPACE"
fi

# testing/helper.py will look for testdata in TINK_PYTHON_ROOT_PATH/testdata.
export TINK_PYTHON_ROOT_PATH="$(pwd)"
# Run Python tests directly so the package is used.
# We exclude tests in tink/cc/pybind: they are implementation details and may
# depend on a testonly shared object.
find tink/ -not -path "*cc/pybind*" -type f -name "*_test.py" -print0 \
  | xargs -0 -n1 python3

# Install requirements for examples.
python3 -m pip install --require-hashes -r examples/requirements.txt

if [[ "${KOKORO_JOB_NAME:-}" =~ .*/pip_kms/.* ]]; then
  # Get root certificates for gRPC
  curl -OLsS https://raw.githubusercontent.com/grpc/grpc/master/etc/roots.pem
  export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="$(pwd)/roots.pem"
  # Run all the *test_package targets, including manual ones that interact with
  # a KMS.
  TARGETS="$(cd examples && "${BAZEL_CMD}" query 'filter(.*test_package, ...)')"
else
  # *test_package targets excluding manual ones.
  TARGETS="$(cd examples \
    && "${BAZEL_CMD}" query \
    'filter(.*test_package, ...) except attr(tags, manual, ...)')"
fi
readonly TARGETS

IFS=' ' read -a TARGETS_ARRAY <<< "$(tr '\n' ' ' <<< "${TARGETS}")"
readonly TARGETS_ARRAY

./kokoro/testutils/run_bazel_tests.sh -m "examples" "${TARGETS_ARRAY[@]}"
