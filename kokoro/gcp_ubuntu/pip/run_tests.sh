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
#  sh ./kokoro/gcp_ubuntu/pip/run_tests.sh
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

./kokoro/testutils/install_tink_via_pip.sh "$(pwd)" ..

# testing/helper.py will look for testdata in TINK_PYTHON_ROOT_PATH/testdata.
export TINK_PYTHON_ROOT_PATH="$(pwd)"
# Run Python tests directly so the package is used.
# We exclude tests in tink/cc/pybind: they are implementation details and may
# depend on a testonly shared object.
find tink/ -not -path "*cc/pybind*" -type f -name "*_test.py" -print0 \
  | xargs -0 -n1 python3
EOF

  chmod +x _do_run_test.sh
}

cleanup() {
  rm -rf _do_run_test.sh
}

main() {
  local run_command_args=()
  if [[ "${IS_KOKORO}" == "true" ]]; then
    TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
    source \
      "${TINK_BASE_DIR}/tink_py/kokoro/testutils/tink_test_container_images.sh"
    CONTAINER_IMAGE="${TINK_PY_BASE_IMAGE}"
    run_command_args+=( -k "${TINK_GCR_SERVICE_KEY}" )
  fi
  : "${TINK_BASE_DIR:=$(cd .. && pwd)}"
  readonly TINK_BASE_DIR
  readonly CONTAINER_IMAGE

  if [[ -n "${CONTAINER_IMAGE:-}" ]]; then
    run_command_args+=( -c "${CONTAINER_IMAGE}" )
  fi

  cd "${TINK_BASE_DIR}/tink_py"

  # Check for dependencies in TINK_BASE_DIR. Any that aren't present will be
  # downloaded.
  ./kokoro/testutils/fetch_git_repo_if_not_present.sh "${TINK_BASE_DIR}" \
    "${GITHUB_ORG}/tink-cc"

  ./kokoro/testutils/copy_credentials.sh "testdata" "all"

  # Run cleanup on EXIT.
  trap cleanup EXIT

  _create_test_command
  # Share the required Kokoro env variables.
  cat <<EOF > env_variables.txt
KOKORO_ROOT
EOF
  run_command_args+=( -e env_variables.txt )
  readonly run_command_args

  ./kokoro/testutils/run_command.sh "${run_command_args[@]}" ./_do_run_test.sh
}

main "$@"
