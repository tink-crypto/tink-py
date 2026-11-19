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
# On Kokoro, the wheels are built in the Tink manylinux image and tested in the
# tink-py base image. When run locally, both steps run directly on the host by
# default. The behavior of this script can be modified using the following
# optional env variables:
#
# - MANYLINUX_CONTAINER_IMAGE (unset by default): Container image to build the
#   wheels in. Building on the host only works on a manylinux host.
# - CONTAINER_IMAGE (unset by default): Container image to test the wheels in.

# Unique hex string of length 20
echo "================================================================================"
echo "Tink Script ID: 3f862eadc2c6d81664cc (to quickly find the script from logs)"
echo "================================================================================"

set -eEuo pipefail

IS_KOKORO="false"
if [[ -n "${KOKORO_ARTIFACTS_DIR:-}" ]]; then
  IS_KOKORO="true"
fi
readonly IS_KOKORO
readonly ARCH="$(uname -m)"

CONTAINER_IMAGE_HASH=
BDIST_CREATE_CMD_ARGS=()
BDIST_TEST_CMD_ARGS=()
if [[ "${IS_KOKORO}" == "true" ]]; then
  readonly TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_py"
  source ./kokoro/testutils/py_test_container_images.sh
  CONTAINER_IMAGE="${TINK_PY_BASE_IMAGE}"
  CONTAINER_IMAGE_HASH="${TINK_PY_BASE_IMAGE_HASH}"
  MANYLINUX_CONTAINER_IMAGE="${TINK_PY_MANYLINUX_IMAGE}"
  if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    CONTAINER_IMAGE="${TINK_PY_BASE_ARM64_IMAGE}"
    CONTAINER_IMAGE_HASH="${TINK_PY_BASE_ARM64_IMAGE_HASH}"
    MANYLINUX_CONTAINER_IMAGE="${TINK_PY_MANYLINUX_ARM64_IMAGE}"
  fi
  BDIST_CREATE_CMD_ARGS+=( -k "${TINK_GCR_SERVICE_KEY}" )
  BDIST_TEST_CMD_ARGS+=( -k "${TINK_GCR_SERVICE_KEY}" )
fi
readonly CONTAINER_IMAGE
readonly CONTAINER_IMAGE_HASH
readonly MANYLINUX_CONTAINER_IMAGE

if [[ -n "${MANYLINUX_CONTAINER_IMAGE:-}" ]]; then
  # The build reads the key for the Bazel remote cache from /tmp/cache_key.
  BDIST_CREATE_CMD_ARGS+=(
    -c "${MANYLINUX_CONTAINER_IMAGE}"
    -m "type=bind,src=/tmp,dst=/tmp"
  )
fi
readonly BDIST_CREATE_CMD_ARGS

if [[ -n "${CONTAINER_IMAGE:-}" ]]; then
  BDIST_TEST_CMD_ARGS+=( -c "${CONTAINER_IMAGE}" )
fi
readonly BDIST_TEST_CMD_ARGS

./kokoro/testutils/copy_credentials.sh "testdata" "all"

CREATE_DIST_OPTIONS=()
if [[ "${KOKORO_JOB_NAME:-}" =~ tink/github/py/.*/release ]]; then
  CREATE_DIST_OPTIONS+=( -t release )
fi

if [[ -n "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET:-}" ]]; then
  rm -rf /tmp/cache_key && cp "${TINK_REMOTE_BAZEL_CACHE_SERVICE_KEY}" \
    /tmp/cache_key
  CREATE_DIST_OPTIONS+=(
    -c "${TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET}/bazel/${CONTAINER_IMAGE_HASH}"
  )
fi
readonly CREATE_DIST_OPTIONS

./kokoro/testutils/docker_execute.sh "${BDIST_CREATE_CMD_ARGS[@]}" \
  ./tools/distribution/create_bdist_linux.sh "${CREATE_DIST_OPTIONS[@]}"

if [[ -n "${MANYLINUX_CONTAINER_IMAGE:-}" ]]; then
  # Docker runs as root so we transfer ownership to the non-root user.
  sudo chown -R "$(id -un):$(id -gn)" "${PWD}"
fi

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

./kokoro/testutils/docker_execute.sh "${BDIST_TEST_CMD_ARGS[@]}" ./_do_test_dist.sh
