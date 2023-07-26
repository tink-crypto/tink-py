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

# Tests the source and binary distributions in a given folder.

set -euox pipefail

readonly PLATFORM="$(uname | tr '[:upper:]' '[:lower:]')"
readonly ARCH="$(uname -m)"

export TINK_PYTHON_ROOT_PATH="${PWD}"

readonly MANYLINUX_X86_64_IMAGE_NAME="quay.io/pypa/manylinux2014_x86_64"
readonly MANYLINUX_X86_64_IMAGE_SHA256="sha256:2f9e5abda045d41f5418216fe7601cf12249989b9aba0a83d009b8cc434cb220"
readonly MANYLINUX_X86_64_IMAGE="${MANYLINUX_X86_64_IMAGE_NAME}@${MANYLINUX_X86_64_IMAGE_SHA256}"

readonly MANYLINUX_AARCH64_IMAGE_NAME="quay.io/pypa/manylinux2014_aarch64"
readonly MANYLINUX_AARCH64_IMAGE_SHA256="sha256:8fd5c58bf1c6a217cddd711144e25af433f2e1f5928245b6e2476affb5d1a76b"
readonly MANYLINUX_AARCH64_IMAGE="${MANYLINUX_AARCH64_IMAGE_NAME}@${MANYLINUX_AARCH64_IMAGE_SHA256}"

usage() {
  echo "Usage:  $0 <release artifacts dir>"
  echo "  -h: Help. Print this usage information."
  exit 1
}

RELEASE_ARTIFACTS_DIR=
parse_args() {
  # Parse options.
  while getopts "h" opt; do
    case "${opt}" in
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  RELEASE_ARTIFACTS_DIR="$1"
  if [[ ! -d "${RELEASE_ARTIFACTS_DIR:-}" ]]; then
    echo -n "InvalidArgumentError: Invalid release folder " >&2
    echo "${RELEASE_ARTIFACTS_DIR:-}" >&2
    exit 1
  fi
  if [[ ! "${PLATFORM}" =~ ^linux$|^darwin$ ]]; then
    echo "InternalError: Unsupported platform ${PLATFORM}" >&2
    exit 1
  fi
  readonly RELEASE_ARTIFACTS_DIR
}

install_dist_and_run_tests() {
  local -r dist="$1"
  if [[ -z "${dist}" || ! -f "${dist}" ]]; then
    echo "InvalidArgumentError: Invalid dist path '${dist}'." >&2
    exit 1
  fi
  python3 -m pip install --require-hashes -r requirements.txt
  python3 -m pip install --no-deps --no-index "${dist}"
  find tink/ -not -path "*cc/pybind*" -type f -name "*_test.py" -print0 \
    | xargs -0 -n1 python3
}

test_linux_wheel_on_manylinux() {
  local -r wheel="$1"
  # Use signatures for getting images from registry (see
  # https://docs.docker.com/engine/security/trust/content_trust/).
  export DOCKER_CONTENT_TRUST=1

  local manylinux_image="${MANYLINUX_X86_64_IMAGE}"
  if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    manylinux_image="${MANYLINUX_AARCH64_IMAGE}"
  fi
  readonly manylinux_image

  docker run \
    --volume "${TINK_PYTHON_ROOT_PATH}:${TINK_PYTHON_ROOT_PATH}" \
    --workdir "${TINK_PYTHON_ROOT_PATH}" \
    "${manylinux_image}" \
    bash -c "./tools/distribution/test_linux_binary_wheel.sh ${wheel}"
}

test_macos_wheel() {
  local -r wheel="$1"
  local -r python_version="$(echo "${wheel}" | grep -oEi 'cp3[0-9]+' | head -1 \
    | sed 's/cp3/3./')"
  enable_py_version "${python_version}"
  install_dist_and_run_tests "${wheel}"
}

enable_py_version() {
  # A partial version number (e.g. "3.9").
  local -r partial_version="$1"
  if [[ -z "${partial_version}" ]]; then
    echo "InvalidArgumentError: Partial version must be specified" >&2
    exit 1
  fi

  # The latest installed Python version that matches the partial version number
  # (e.g. "3.9.5").
  local version="$(pyenv versions --bare | grep "${partial_version}" | tail -1)"
  if [[ -z "${version}" ]]; then
    # Install the latest available.
    version="$(pyenv install --list | grep "  ${partial_version}" | tail -1 \
      | xargs)"
    pyenv install "${version}"
  fi
  readonly version
  # Set current Python version via environment variable.
  pyenv shell "${version}"
  # Update environment.
  python3 -m pip install --require-hashes -r \
    "${TINK_PYTHON_ROOT_PATH}/tools/distribution/requirements.txt"
}

is_sdist() {
  local -r dist="$1"
  if [[ "${dist}" =~ tink-.*tar.gz$ ]]; then
    return 0
  fi
  return 1
}

main() {
  parse_args "$@"

  eval "$(pyenv init -)"

  for dist in "${RELEASE_ARTIFACTS_DIR}/tink-"*; do
    if is_sdist "${dist}"; then
      install_dist_and_run_tests "${dist}"
    else
      # Binary wheels.
      case "${PLATFORM}" in
        linux)
          test_linux_wheel_on_manylinux "${dist}"
          ;;
        darwin)
          test_macos_wheel "${dist}"
          ;;
        *)
          echo "InternalError: Invalid platform ${PLATFORM}" >&2
          exit 1
          ;;
      esac
    fi
  done
}

main "$@"
