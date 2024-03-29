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

# Builds and tests tink-py and its examples using Bazel.
#
# The behavior of this script can be modified using the following optional env
# variables:
#
# - CONTAINER_IMAGE (unset by default): By default when run locally this script
#   executes tests directly on the host. The CONTAINER_IMAGE variable can be set
#   to execute tests in a custom container image for local testing. E.g.:
#
#   CONTAINER_IMAGE="us-docker.pkg.dev/tink-test-infrastructure/tink-ci-images/linux-tink-py-base:latest" \
#     sh ./kokoro/gcp_ubuntu/bazel/run_tests.sh
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

# Build tink-py and run unit tests.
./kokoro/testutils/run_bazel_tests.sh .
if [[ "${KOKORO_JOB_NAME:-}" =~ .*/bazel_kms/.* ]]; then
  source ./kokoro/testutils/install_vault.sh
  source ./kokoro/testutils/run_hcvault_test_server.sh
  vault write -f transit/keys/key-1

  readonly MANUAL_TARGETS="$(
    "${BAZEL_CMD}" query 'attr(tags, manual, kind(.*_test, ...))')"
  IFS=' ' read -a MANUAL_TARGETS_ARRAY <<< "$(tr '\n' ' ' \
    <<< "${MANUAL_TARGETS}")"
  readonly MANUAL_TARGETS_ARRAY

  # Make sure VAULT_ADDR and VAULT_TOKEN are available to the Bazel tests.
  MANUAL_TARGETS_TEST_ARGS="--test_env=VAULT_ADDR=${VAULT_ADDR}"
  MANUAL_TARGETS_TEST_ARGS+=",--test_env=VAULT_TOKEN=${VAULT_TOKEN}"
  readonly MANUAL_TARGETS_TEST_ARGS
  ./kokoro/testutils/run_bazel_tests.sh -m -t  "${MANUAL_TARGETS_TEST_ARGS}" . \
    "${MANUAL_TARGETS_ARRAY[@]}"
fi

# Run examples tests.
if [[ "${KOKORO_JOB_NAME:-}" =~ .*/bazel_kms/.* ]]; then
  # Run all the test targets excluding *test_package, including manual ones that
  # interact with a KMS.

  #TODO(b/276277854) It is not clear why this is needed.
  python3 -m pip install --require-hashes --no-deps -r examples/requirements.txt

  TARGETS="$(cd examples && "${BAZEL_CMD}" query \
    'kind(.*_test, ...) except filter(.*test_package, ...)')"
else
  # Run all the test targets excluding *test_package, exclude manual ones.
  TARGETS="$(cd examples \
    && "${BAZEL_CMD}" query \
      'kind(.*_test, ...) except filter(.*test_package, ...) except attr(tags, manual, ...)')"
fi
readonly TARGETS

IFS=' ' read -a TARGETS_ARRAY <<< "$(tr '\n' ' ' <<< "${TARGETS}")"
readonly TARGETS_ARRAY

./kokoro/testutils/run_bazel_tests.sh -m "examples" "${TARGETS_ARRAY[@]}"
EOF

  chmod +x _do_run_test.sh
}

_cleanup() {
  rm -rf env_variables.txt
  rm -rf _do_run_test.sh
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

  _create_test_command

  trap _cleanup EXIT

  # Share the required Kokoro env variables.
  cat <<EOF > env_variables.txt
KOKORO_ROOT
KOKORO_JOB_NAME
EOF
  run_command_args+=( -e env_variables.txt )
  readonly run_command_args
  ./kokoro/testutils/run_command.sh "${run_command_args[@]}" ./_do_run_test.sh
}

main "$@"
