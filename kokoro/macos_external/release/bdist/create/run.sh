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

# Creates and tests a binary wheel distribution.
#
# The behavior of this script can be modified using the following optional env
# variables:
#
# - USE_LOCAL_TINK_CC ("true" by default): If true, the script  uses a local
#   version of tink_cc located at TINK_BASE_DIR (see below).
#   NOTE: tink_cc is fetched from GitHub if not found.
#
# - TINK_BASE_DIR (../ by default): This is the folder where to look for
#   tink-py and its dependencies. That is ${TINK_BASE_DIR}/tink_py and
#   optionally ${TINK_BASE_DIR}/tink_cc.
set -eEuo pipefail

IS_KOKORO="false"
if [[ -n "${KOKORO_ARTIFACTS_DIR:-}" ]]; then
  IS_KOKORO="true"
fi
readonly IS_KOKORO

if [[ -z "${USE_LOCAL_TINK_CC:-}" ]]; then
  if [[ "${KOKORO_JOB_NAME:-}" =~ tink/github/py/.*/release ]]; then
    USE_LOCAL_TINK_CC="false"
  else
    USE_LOCAL_TINK_CC="true"
  fi
fi
readonly USE_LOCAL_TINK_CC

if [[ "${IS_KOKORO}" == "true" ]]; then
  TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
fi
: "${TINK_BASE_DIR:=$(cd .. && pwd)}"
readonly TINK_BASE_DIR

cd "${TINK_BASE_DIR}/tink_py"

# Check for dependencies in TINK_BASE_DIR. Any that aren't present will be
# downloaded.
readonly GITHUB_ORG="https://github.com/tink-crypto"
./kokoro/testutils/fetch_git_repo_if_not_present.sh "${TINK_BASE_DIR}" \
  "${GITHUB_ORG}/tink-cc"

./kokoro/testutils/copy_credentials.sh "testdata" "all"

CREATE_DIST_OPTIONS=()
if [[ "${KOKORO_JOB_NAME:-}" =~ tink/github/py/.*/release ]]; then
  CREATE_DIST_OPTIONS+=( -t release )
else
  CREATE_DIST_OPTIONS+=( -t dev )
fi
readonly CREATE_DIST_OPTIONS

if [[ "${USE_LOCAL_TINK_CC}" == "true" ]]; then
  sed -i '.bak' 's~# Placeholder for tink-cc override.~\
local_repository(\
  name = "tink_cc",\
  path = "../tink_cc",\
)~' WORKSPACE
fi

./tools/distribution/create_bdist.sh "${CREATE_DIST_OPTIONS[@]}"
./tools/distribution/test_dist.sh release

if [[ -f "WORKSPACE.bak" ]]; then
  mv "WORKSPACE.bak" "WORKSPACE"
fi
