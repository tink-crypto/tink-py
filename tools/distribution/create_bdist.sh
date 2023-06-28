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

# This script creates binary wheels for Tink Python for Linux and macOS.

set -eEuox pipefail

declare -a PYTHON_VERSIONS=
PYTHON_VERSIONS+=("3.7")
PYTHON_VERSIONS+=("3.8")
PYTHON_VERSIONS+=("3.9")
PYTHON_VERSIONS+=("3.10")
readonly PYTHON_VERSIONS

readonly PLATFORM="$(uname | tr '[:upper:]' '[:lower:]')"

export TINK_PYTHON_ROOT_PATH="${PWD}"

readonly IMAGE_NAME="quay.io/pypa/manylinux2014_x86_64"
readonly IMAGE_DIGEST="sha256:31d7d1cbbb8ea93ac64c3113bceaa0e9e13d65198229a25eee16dc70e8bf9cf7"
readonly IMAGE="${IMAGE_NAME}@${IMAGE_DIGEST}"

usage() {
  cat <<EOF
Usage:  $0 [-l] [-t <release type (dev|release)>]
  -l: [Optional] If set build binary wheels against a local tink-cc located at ${PWD}/..
  -t: [Optional] Type of release; if "dev", the genereted wheels use <version from VERSION>-dev0; if "release", <version from VERSION> (default=dev).
  -h: Help. Print this usage information.
EOF
  exit 1
}

TINK_CC_USE_LOCAL="false"
RELEASE_TYPE="dev"
TINK_VERSION=

parse_args() {
  # Parse options.
  while getopts "hlt:" opt; do
    case "${opt}" in
      l) TINK_CC_USE_LOCAL="true" ;;
      t) RELEASE_TYPE="${OPTARG}" ;;
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  readonly TINK_CC_USE_LOCAL
  readonly RELEASE_TYPE

  TINK_VERSION="$(grep ^TINK "VERSION" | awk '{gsub(/"/, "", $3); print $3}')"
  case "${RELEASE_TYPE}" in
    dev) TINK_VERSION="${TINK_VERSION}.dev0" ;;
    release) ;;
    *)
      echo "ERROR: Invalid release type ${RELEASE_TYPE}" >&2
      usage
      ;;
  esac
  readonly TINK_VERSION
}

cleanup() {
  mv WORKSPACE.bak WORKSPACE
}

#######################################
# Builds Tink Python built distribution (Wheel) [1].
#
# This function must be called from within the Tink Python's root folder.
#
# [1] https://packaging.python.org/en/latest/glossary/#term-Built-Distribution
# Globals:
#   None
# Arguments:
#   None
#######################################
create_bdist_for_linux() {
  echo "### Building and testing Linux binary wheels ###"
  # Use signatures for getting images from registry (see
  # https://docs.docker.com/engine/security/trust/content_trust/).
  export DOCKER_CONTENT_TRUST=1

  # We use setup.py to build wheels; setup.py makes changes to the WORKSPACE
  # file so we save a copy for backup.
  cp WORKSPACE WORKSPACE.bak

  trap cleanup EXIT

  # Base directory in the container image.
  local -r tink_deps_container_dir="/tmp/tink"
  local -r tink_py_relative_path="${PWD##*/}"
  # Path to tink-py within the container.
  local -r tink_py_container_dir="${tink_deps_container_dir}/${tink_py_relative_path}"

  local env_variables=(
    -e TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION="${TINK_VERSION}"
  )
  if [[ "${TINK_CC_USE_LOCAL}" == "true" ]]; then
    env_variables+=(
      -e TINK_PYTHON_SETUPTOOLS_OVERRIDE_BASE_PATH="${tink_deps_container_dir}"
    )
  fi
  readonly env_variables

  # Build binary wheels.
  docker run \
    --volume "${TINK_PYTHON_ROOT_PATH}/..:${tink_deps_container_dir}" \
    --workdir "${tink_py_container_dir}" \
    "${env_variables[@]}" \
    "${IMAGE}" \
    "${tink_py_container_dir}/tools/distribution/build_linux_binary_wheels.sh"

  ## Test binary wheels.
  docker run \
    --volume "${TINK_PYTHON_ROOT_PATH}/..:${tink_deps_container_dir}" \
    --workdir "${tink_py_container_dir}" \
    "${IMAGE}" \
    "${tink_py_container_dir}/tools/distribution/test_linux_binary_wheels.sh"

  # Docker runs as root so we transfer ownership to the non-root user.
  sudo chown -R "$(id -un):$(id -gn)" "${TINK_PYTHON_ROOT_PATH}"
}

#######################################
# Creates a Tink Python distribution for MacOS.
#
# This function must be called from within the Tink Python's root folder.
#
# Globals:
#   PYTHON_VERSIONS
# Arguments:
#   None
#######################################
create_bdist_for_macos() {
  echo "### Building macOS binary wheels ###"

  export TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION="${TINK_VERSION}"
  rm -rf release && mkdir -p release
  for python_version in "${PYTHON_VERSIONS[@]}"; do
    enable_py_version "${python_version}"

    build_dir="$(mktemp -d -t release.XXXXX)"
    # Build binary wheel.
    python3 -m pip wheel -w "${build_dir}" .
    mv "${build_dir}/tink-${TINK_VERSION}"* release/

    # Test binary wheel.
    # TODO(ckl): Implement test.
  done
}

enable_py_version() {
  # A partial version number (e.g. "3.9").
  local -r partial_version="$1"

  # The latest installed Python version that matches the partial version number
  # (e.g. "3.9.5").
  local -r version="$(pyenv versions --bare | grep "${partial_version}" \
    | tail -1)"

  # Set current Python version via environment variable.
  pyenv shell "${version}"

  # Update environment.
  python3 -m pip install --require-hashes -r \
    "${TINK_PYTHON_ROOT_PATH}/tools/distribution/requirements.txt"
}

main() {
  parse_args "$@"

  eval "$(pyenv init -)"
  mkdir -p release

  if [[ "${PLATFORM}" == 'linux' ]]; then
    create_bdist_for_linux
  elif [[ "${PLATFORM}" == 'darwin' ]]; then
    create_bdist_for_macos
  else
    echo "${PLATFORM} is not a supported platform."
    exit 1
  fi
}

main "$@"
