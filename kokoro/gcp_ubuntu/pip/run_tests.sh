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
#     sh ./kokoro/gcp_ubuntu/pip/run_tests.sh
#
set -eEuo pipefail

IS_KOKORO="false"
if [[ -n "${KOKORO_ARTIFACTS_DIR:-}" ]]; then
  IS_KOKORO="true"
fi
readonly IS_KOKORO

_create_test_command() {
  cat <<'EOF' > _do_run_test.sh
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

# testing/helper.py will look for testdata in TINK_PYTHON_ROOT_PATH/testdata.
export TINK_PYTHON_ROOT_PATH="$(pwd)"

TEST_EXCLUDE=( -not -path "*cc/pybind*" )
if [[ "${TEST_WITH_KMS}" == "true" ]]; then
  ./kokoro/testutils/install_tink_via_pip.sh -a "$(pwd)"
else
  ./kokoro/testutils/install_tink_via_pip.sh "$(pwd)"
  TEST_EXCLUDE+=( -not -path "*integration/*" )
fi
readonly TEST_EXCLUDE
find tink/ "${TEST_EXCLUDE}" -type f -name "*_test.py" -print0 \
  | xargs -0 -n1 python3

# Install requirements for examples.
python3 -m pip install --require-hashes -r examples/requirements.txt
if [[ "${TEST_WITH_KMS}" == "true" ]]; then
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
EOF

  chmod +x _do_run_test.sh
}

cleanup() {
  rm -rf _do_run_test.sh
  rm -rf env_variables.txt
}

main() {
  local run_command_args=()
  if [[ "${IS_KOKORO}" == "true" ]]; then
    readonly TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
    cd "${TINK_BASE_DIR}/tink_py"
    source ./kokoro/testutils/py_test_container_images.sh
    CONTAINER_IMAGE="${TINK_PY_BASE_IMAGE}"
    run_command_args+=( -k "${TINK_GCR_SERVICE_KEY}" )
  fi
  readonly CONTAINER_IMAGE

  if [[ -n "${CONTAINER_IMAGE:-}" ]]; then
    run_command_args+=( -c "${CONTAINER_IMAGE}" )
  fi

  ./kokoro/testutils/copy_credentials.sh "testdata" "all"
  ./kokoro/testutils/copy_credentials.sh "examples/testdata" "gcp"

  # Run cleanup on EXIT.
  trap cleanup EXIT

  _create_test_command
  # Share the required env variables.
  cat <<EOF > env_variables.txt
KOKORO_ROOT
KOKORO_JOB_NAME
EOF
  run_command_args+=( -e env_variables.txt )
  readonly run_command_args

  ./kokoro/testutils/run_command.sh "${run_command_args[@]}" ./_do_run_test.sh
}

main "$@"
