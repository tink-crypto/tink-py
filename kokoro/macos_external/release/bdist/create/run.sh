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

# Unique hex string of length 20
echo "================================================================================"
echo "Tink Script ID: d329ed3b9a74649b63f1 (to quickly find the script from logs)"
echo "================================================================================"

set -eEuo pipefail

IS_KOKORO="false"
if [[ -n "${KOKORO_ARTIFACTS_DIR:-}" ]]; then
  IS_KOKORO="true"
fi
readonly IS_KOKORO

if [[ "${IS_KOKORO}" == "true" ]]; then
  readonly TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_py"
fi

./kokoro/testutils/copy_credentials.sh "testdata" "all"

CREATE_DIST_OPTIONS=()
if [[ "${KOKORO_JOB_NAME:-}" =~ tink/github/py/.*/release ]]; then
  CREATE_DIST_OPTIONS+=( -t release )
else
  CREATE_DIST_OPTIONS+=( -t dev )
fi
if [[ -n "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET:-}" ]]; then
  cp "${TINK_REMOTE_BAZEL_CACHE_SERVICE_KEY}" /tmp/cache_key
  CREATE_DIST_OPTIONS+=( -c "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET}/bazel/macos_tink_py" )
fi
readonly CREATE_DIST_OPTIONS

# Sourcing required to update callers environment.
# NOTE: See
# https://github.com/tink-crypto/tink-py/issues/60#issuecomment-4405494880 for
# why we need 5.29.5.
source ./kokoro/testutils/install_protoc.sh "29.5"

# The pre-installed pyenv on Kokoro macOS 15 images is too old for the Python
# versions that create_bdist.sh and test_dist.sh install, see
# install_pyenv.sh. Sourcing required to update callers environment.
source ./kokoro/testutils/install_pyenv.sh

./tools/distribution/create_bdist.sh "${CREATE_DIST_OPTIONS[@]}"

source ./kokoro/testutils/install_vault.sh
source ./kokoro/testutils/run_hcvault_test_server.sh
vault write -f transit/keys/key-1

./tools/distribution/test_dist.sh release
