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
set -eEuo pipefail

IS_KOKORO="false"
if [[ -n "${KOKORO_ARTIFACTS_DIR:-}" ]]; then
  IS_KOKORO="true"
fi
readonly IS_KOKORO
readonly ARCH="$(uname -m)"

RUN_COMMAND_ARGS=()
if [[ "${IS_KOKORO}" == "true" ]]; then
  readonly TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_py"
  source ./kokoro/testutils/py_test_container_images.sh
  CONTAINER_IMAGE="${TINK_PY_BASE_IMAGE}"
  if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    CONTAINER_IMAGE="${TINK_PY_BASE_ARM64_IMAGE}"
  fi
  RUN_COMMAND_ARGS+=( -k "${TINK_GCR_SERVICE_KEY}" )
fi
readonly CONTAINER_IMAGE

if [[ -n "${CONTAINER_IMAGE:-}" ]]; then
  RUN_COMMAND_ARGS+=( -c "${CONTAINER_IMAGE}" )
fi
readonly RUN_COMMAND_ARGS

./kokoro/testutils/copy_credentials.sh "testdata" "all"

CREATE_DIST_OPTIONS=()
if [[ "${KOKORO_JOB_NAME:-}" =~ tink/github/py/.*/release ]]; then
  CREATE_DIST_OPTIONS+=( -t release )
fi

if [[ -n "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET:-}" ]]; then
  cp "${TINK_REMOTE_BAZEL_CACHE_SERVICE_KEY}" /tmp/cache_key
  CREATE_DIST_OPTIONS+=( -c "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET}/bazel/${TINK_PY_BASE_IMAGE_HASH}" )
fi
readonly CREATE_DIST_OPTIONS

./tools/distribution/create_bdist.sh "${CREATE_DIST_OPTIONS[@]}"

cat <<'EOF' > _do_test_dist.sh
set -euo pipefail

source ./kokoro/testutils/install_vault.sh
source ./kokoro/testutils/run_hcvault_test_server.sh
vault write -f transit/keys/key-1
./tools/distribution/test_dist.sh release
EOF
chmod +x _do_test_dist.sh

trap cleanup EXIT

cleanup() {
  rm -rf _do_test_dist.sh
}

./kokoro/testutils/run_command.sh "${RUN_COMMAND_ARGS[@]}" ./_do_test_dist.sh
