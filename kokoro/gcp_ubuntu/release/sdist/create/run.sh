#!/bin/bash
# Copyright 2023 Google LLC
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
#  sh ./kokoro/gcp_ubuntu/release/sdist/create.sh
#
# The user may specify TINK_BASE_DIR as the folder where to look for tink-py
# and its dependencies. That is:
#   ${TINK_BASE_DIR}/tink_cc
#   ${TINK_BASE_DIR}/tink_py
# NOTE: tink_cc is fetched from GitHub if not found.
set -eEuo pipefail

IS_KOKORO="false"
if [[ -n "${KOKORO_ARTIFACTS_DIR:-}" ]]; then
  IS_KOKORO="true"
fi
readonly IS_KOKORO

RUN_COMMAND_ARGS=()
if [[ "${IS_KOKORO}" == "true" ]]; then
  TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
    source \
      "${TINK_BASE_DIR}/tink_py/kokoro/testutils/py_test_container_images.sh"
    CONTAINER_IMAGE="${TINK_PY_BASE_IMAGE}"
  RUN_COMMAND_ARGS+=( -k "${TINK_GCR_SERVICE_KEY}" )
fi
: "${TINK_BASE_DIR:=$(cd .. && pwd)}"
readonly TINK_BASE_DIR
readonly CONTAINER_IMAGE

if [[ -n "${CONTAINER_IMAGE:-}" ]]; then
  RUN_COMMAND_ARGS+=( -c "${CONTAINER_IMAGE}" )
fi
readonly RUN_COMMAND_ARGS

cd "${TINK_BASE_DIR}/tink_py"

# Check for dependencies in TINK_BASE_DIR. Any that aren't present will be
# downloaded.
readonly GITHUB_ORG="https://github.com/tink-crypto"
./kokoro/testutils/fetch_git_repo_if_not_present.sh "${TINK_BASE_DIR}" \
  "${GITHUB_ORG}/tink-cc"

CREATE_DIST_OPTIONS=()
if [[ "${IS_KOKORO}" == "true" ]]; then
  if [[ "${KOKORO_PARENT_JOB_NAME:-}" =~ tink/github/py/.*_release ]]; then
    CREATE_DIST_OPTIONS+=( -t release )
  else
    sed -i'.bak' 's~# Placeholder for tink-cc override.~\
local_repository(\
    name = "tink_cc",\
    path = "../tink_cc",\
)~' WORKSPACE
  fi
fi
readonly CREATE_DIST_OPTIONS

_cleanup() {
  if [[ -f "WORKSPACE.bak" ]]; then
    mv "WORKSPACE.bak" "WORKSPACE"
  fi
}

trap _cleanup EXIT

# Generate a source distribution.
./kokoro/testutils/run_command.sh "${RUN_COMMAND_ARGS[@]}" \
  ./tools/distribution/create_sdist.sh "${CREATE_DIST_OPTIONS[@]}"
