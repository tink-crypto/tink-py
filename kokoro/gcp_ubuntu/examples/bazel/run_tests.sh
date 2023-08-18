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

# By default when run locally this script executes tests directly on the host.
# The CONTAINER_IMAGE variable can be set to execute tests in a custom container
# image for local testing. E.g.:
#
# CONTAINER_IMAGE="us-docker.pkg.dev/tink-test-infrastructure/tink-ci-images/linux-tink-py-base:latest" \
#  sh ./kokoro/gcp_ubuntu/examples/bazel/run_tests.sh
#
# The user may specify TINK_BASE_DIR as the folder where to look for tink-py
# and its dependencies. That is:
#   ${TINK_BASE_DIR}/tink_cc
#   ${TINK_BASE_DIR}/tink_py
# NOTE: tink_cc is fetched from GitHub if not found.
set -eEuo pipefail

readonly GITHUB_ORG="https://github.com/tink-crypto"

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

# All .*_test targets except manual and *test_package ones.
readonly MANUAL_TARGETS="$(cd examples \
  && "${BAZEL_CMD}" query \
    'kind(.*_test, ...) except attr(tags, manual, ...) except filter(.*test_package, ...)')"
IFS=' ' read -a MANUAL_TARGETS_ARRAY \
  <<< "$(tr '\n' ' ' <<< "${MANUAL_TARGETS}")"
readonly MANUAL_TARGETS_ARRAY

./kokoro/testutils/run_bazel_tests.sh -m "examples" "${MANUAL_TARGETS_ARRAY[@]}"
EOF

  chmod +x _do_run_test.sh
}

cleanup() {
  rm -rf _do_run_test.sh
  mv "WORKSPACE.bak" "WORKSPACE"
}

main() {
  local run_command_args=()
  if [[ "${IS_KOKORO}" == "true" ]]; then
    TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
    source \
      "${TINK_BASE_DIR}/tink_py/kokoro/testutils/py_test_container_images.sh"
    CONTAINER_IMAGE="${TINK_PY_BASE_IMAGE}"
    run_command_args+=( -k "${TINK_GCR_SERVICE_KEY}" )
  fi
  : "${TINK_BASE_DIR:=$(cd .. && pwd)}"
  readonly TINK_BASE_DIR
  readonly CONTAINER_IMAGE

  if [[ -n "${CONTAINER_IMAGE:-}" ]]; then
    run_command_args+=( -c "${CONTAINER_IMAGE}" )
  fi
  readonly run_command_args

  cd "${TINK_BASE_DIR}/tink_py"

  # Check for dependencies in TINK_BASE_DIR. Any that aren't present will be
  # downloaded.
  ./kokoro/testutils/fetch_git_repo_if_not_present.sh "${TINK_BASE_DIR}" \
    "${GITHUB_ORG}/tink-cc"

  cp "WORKSPACE" "WORKSPACE.bak"
  ./kokoro/testutils/replace_http_archive_with_local_repository.py \
    -f "WORKSPACE" -t ..

  # Run cleanup on EXIT.
  trap cleanup EXIT

  _create_test_command

  ./kokoro/testutils/run_command.sh "${run_command_args[@]}" ./_do_run_test.sh
}

main "$@"
