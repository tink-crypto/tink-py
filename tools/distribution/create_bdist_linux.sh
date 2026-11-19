#!/bin/bash
# Copyright 2020 Google LLC
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

# Generated with openssl rand -hex 10
echo "================================================================================"
echo "Tink Script ID: 87b6b958a7ce24607cca (to quickly find the script from logs)"
echo "================================================================================"

set -eEuox pipefail

# This script creates binary wheels for Tink Python for Linux and macOS.

readonly GCS_URL="https://storage.googleapis.com"

export TINK_PYTHON_ROOT_PATH="${PWD}"

readonly MANYLINUX_X86_64_IMAGE_NAME="quay.io/pypa/manylinux_2_28_x86_64"
readonly MANYLINUX_X86_64_IMAGE_SHA256="sha256:e0adf18521ad35192df733a6c62d35df7801957d24e0470238aacecfab2188a3"
readonly MANYLINUX_X86_64_IMAGE="${MANYLINUX_X86_64_IMAGE_NAME}@${MANYLINUX_X86_64_IMAGE_SHA256}"

readonly MANYLINUX_AARCH64_IMAGE_NAME="quay.io/pypa/manylinux_2_28_aarch64"
readonly MANYLINUX_AARCH64_IMAGE_SHA256="sha256:a3e02308c822fb6ce0d12248b0c941817ba5e1a1bc9e7bb5929f29c50eaa40a9"
readonly MANYLINUX_AARCH64_IMAGE="${MANYLINUX_AARCH64_IMAGE_NAME}@${MANYLINUX_AARCH64_IMAGE_SHA256}"

usage() {
  cat <<EOF
Usage:  $0 [-c Bazel cache name] [-t <release type (dev|release)>]
  -t: [Optional] Type of release; if "dev", the genereted wheels use <version
      from TINK_VERSION.txt>-dev0; if "release", <version from TINK_VERSION.txt>
      (default=dev).
  -c: [Optional] Bazel cache to use; credentials are expected to be in a
      /tmp/cache_key file.
  -h: Help. Print this usage information.
EOF
  exit 1
}

RELEASE_TYPE="dev"
TINK_VERSION=
BAZEL_CACHE_NAME=

parse_args() {
  # Parse options.
  while getopts "ht:c:" opt; do
    case "${opt}" in
      t) RELEASE_TYPE="${OPTARG}" ;;
      c) BAZEL_CACHE_NAME="${OPTARG}" ;;
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  readonly RELEASE_TYPE
  readonly BAZEL_CACHE_NAME
  TINK_VERSION="$(cat TINK_VERSION.txt)"
  case "${RELEASE_TYPE}" in
    dev) TINK_VERSION="${TINK_VERSION}.dev0" ;;
    release) ;;
    *)
      echo "InvalidArgumentError: Invalid release type ${RELEASE_TYPE}" >&2
      usage
      ;;
  esac
  readonly TINK_VERSION
}

#######################################
# Builds Tink Python built distribution (Wheel) [1].
#
# This function must be called from within the Tink Python's root folder.
#
# [1] https://packaging.python.org/en/latest/glossary/#term-Built-Distribution
# Globals:
#   TINK_VERSION
#   BAZEL_CACHE_NAME
#   GCS_URL
#   TINK_PYTHON_ROOT_PATH
# Arguments:
#   None
#######################################
create_bdist_for_linux() {
  echo "### Building and testing Linux binary wheels ###"
  eval "$(pyenv init -)"

  rm -rf release && mkdir -p release

  # Use signatures for getting images from registry (see
  # https://docs.docker.com/engine/security/trust/content_trust/).
  export DOCKER_CONTENT_TRUST=1

  local env_variables=(
    -e TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION="${TINK_VERSION}"
  )
  if [[ -n "${BAZEL_CACHE_NAME:-}" ]]; then
    env_variables+=(
      -e TINK_PYTHON_BAZEL_REMOTE_CACHE_GCS_BUCKET_URL="${GCS_URL}/${BAZEL_CACHE_NAME}"
      -e TINK_PYTHON_BAZEL_REMOTE_CACHE_SERVICE_KEY_PATH="/tmp/cache_key"
    )
  fi
  readonly env_variables

  readonly arch="$(uname -m)"
  local manylinux_image=""
  case "${arch}" in
    x86_64)
      manylinux_image="${MANYLINUX_X86_64_IMAGE}"
      ;;
    aarch64|arm64)
      manylinux_image="${MANYLINUX_AARCH64_IMAGE}"
      ;;
    *)
      echo "InvalidArgumentError: Unsupported architecture ${arch}" >&2
      exit 1
      ;;
  esac
  readonly manylinux_image

  # Build binary wheels. Mount the tink python root folder and the tmp folder.
  docker run \
    --volume "${TINK_PYTHON_ROOT_PATH}:/tink" --volume "/tmp:/tmp" \
    --workdir "/tink" "${env_variables[@]}" "${manylinux_image}" \
    "tools/distribution/build_linux_binary_wheels.sh"

  # Docker runs as root so we transfer ownership to the non-root user.
  sudo chown -R "$(id -un):$(id -gn)" "${TINK_PYTHON_ROOT_PATH}"
}

main() {
  parse_args "$@"

  readonly platform="$(uname | tr '[:upper:]' '[:lower:]')"
  case "${platform}" in
    linux)
      create_bdist_for_linux
      ;;
    *)
      echo "InvalidArgumentError: Unsupported platform ${platform}" >&2
      exit 1
      ;;
  esac
}

main "$@"
