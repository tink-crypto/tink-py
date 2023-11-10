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

readonly PYTHON_VERSIONS=( "3.8" "3.9" "3.10" "3.11" )

readonly PLATFORM="$(uname | tr '[:upper:]' '[:lower:]')"

export TINK_PYTHON_ROOT_PATH="${PWD}"

readonly MANYLINUX_X86_64_IMAGE_NAME="quay.io/pypa/manylinux2014_x86_64"
readonly MANYLINUX_X86_64_IMAGE_SHA256="sha256:2f9e5abda045d41f5418216fe7601cf12249989b9aba0a83d009b8cc434cb220"
readonly MANYLINUX_X86_64_IMAGE="${MANYLINUX_X86_64_IMAGE_NAME}@${MANYLINUX_X86_64_IMAGE_SHA256}"

readonly MANYLINUX_AARCH64_IMAGE_NAME="quay.io/pypa/manylinux2014_aarch64"
readonly MANYLINUX_AARCH64_IMAGE_SHA256="sha256:8fd5c58bf1c6a217cddd711144e25af433f2e1f5928245b6e2476affb5d1a76b"
readonly MANYLINUX_AARCH64_IMAGE="${MANYLINUX_AARCH64_IMAGE_NAME}@${MANYLINUX_AARCH64_IMAGE_SHA256}"

readonly ARCH="$(uname -m)"

usage() {
  cat <<EOF
Usage:  $0 [-t <release type (dev|release)>]
  -t: [Optional] Type of release; if "dev", the genereted wheels use <version from VERSION>-dev0; if "release", <version from VERSION> (default=dev).
  -h: Help. Print this usage information.
EOF
  exit 1
}

RELEASE_TYPE="dev"
TINK_VERSION=

parse_args() {
  # Parse options.
  while getopts "ht:" opt; do
    case "${opt}" in
      t) RELEASE_TYPE="${OPTARG}" ;;
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  readonly RELEASE_TYPE

  TINK_VERSION="$(cat VERSION)"
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
#   None
# Arguments:
#   None
#######################################
create_bdist_for_linux() {
  echo "### Building and testing Linux binary wheels ###"
  # Use signatures for getting images from registry (see
  # https://docs.docker.com/engine/security/trust/content_trust/).
  export DOCKER_CONTENT_TRUST=1

  # Base directory in the container image.
  local -r tink_deps_container_dir="/tmp/tink"
  local -r tink_py_relative_path="${PWD##*/}"
  # Path to tink-py within the container.
  local -r tink_py_container_dir="${tink_deps_container_dir}/${tink_py_relative_path}"

  local env_variables=(
    -e TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION="${TINK_VERSION}"
  )
  readonly env_variables

  local manylinux_image="${MANYLINUX_X86_64_IMAGE}"
  if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    manylinux_image="${MANYLINUX_AARCH64_IMAGE}"
  fi
  readonly manylinux_image

  # Build binary wheels.
  docker run \
    --volume "${TINK_PYTHON_ROOT_PATH}/..:${tink_deps_container_dir}" \
    --workdir "${tink_py_container_dir}" \
    "${env_variables[@]}" \
    "${manylinux_image}" \
    "${tink_py_container_dir}/tools/distribution/build_linux_binary_wheels.sh"

  # Docker runs as root so we transfer ownership to the non-root user.
  sudo chown -R "$(id -un):$(id -gn)" "${TINK_PYTHON_ROOT_PATH}"
}

#######################################
# Creates a binary wheel for Tink Python on macOS.
#
# This function must be called from within the Tink Python's root folder.
#
# Arguments:
#   min_macos_version: Target minimum macOS version.
#   arch: Target arch (x86_64 or arm64).
#   out_dir: Path where to store the generated wheels.
#######################################
_build_wheel_for_macos() {
  local -r min_macos_version="${1:-}"
  local -r arch="${2:-}"
  local -r out_dir="${3:-}"

  if [[ ! "${min_macos_version}" =~ ^[0-9]+.[0-9]+$ ]]; then
    echo "InvalidArgumentError: Invalid macOS version ${min_macos_version}" >&2
    exit 1
  fi

  if [[ "${arch}" != "x86_64" && "${arch}" != "arm64" ]]; then
    echo -n "InvalidArgumentError: Unsupported architecture ${arch}, " >&2
    echo "only x86_64 and arm64 are supported" >&2
    exit 1
  fi

  if [[ ! -d "${out_dir}" ]]; then
    echo "InvalidArgumentError: Output folder ${out_dir} does not exist" >&2
    exit 1
  fi

  (
    export MACOSX_DEPLOYMENT_TARGET="${min_macos_version}"
    export _PYTHON_HOST_PLATFORM="macosx-${min_macos_version}-${arch}"
    export ARCHFLAGS="-arch ${arch}"
    time python3 -m pip wheel -w "${out_dir}" .
  )
}

#######################################
# Creates a universal2 wheel from an x86_64 wheel and an arm64 wheel.
#
# The function uses delocate (https://pypi.org/project/delocate/) to combine
# both wheels into a universal2 wheel.
#
# Arguments:
#   arm64_whl: arm64 wheel.
#   x86_whl: x86_64 wheel.
#   out_dir: Path where to store the generated wheel.
#######################################
_create_universal2_macos_wheel() {
  local -r arm64_whl="${1:-}"
  local -r x86_whl="${2:-}"
  local -r out_dir="${3:-$(pwd)}"

  if [[ ! -d "${out_dir}" ]]; then
    echo "InvalidArgumentError: Output folder ${out_dir} does not exist" >&2
    exit 1
  fi

  # NOTE: The resulting wheel is named after the 1st parameter (in this case
  # arm64_whl). We thus use a separate folder to avoid delocate to overwrite it.
  local -r tmp_build_dir="$(mktemp -d -t universal2)"
  time python3 -m delocate.cmd.delocate_fuse "${arm64_whl}" "${x86_whl}" \
    -w "${tmp_build_dir}"
  local -r generated_whl="${tmp_build_dir}/$(basename "${arm64_whl}")"
  local -r rename_to="${out_dir}/$(basename ${generated_whl//arm64/universal2})"
  mv "${generated_whl}" "${rename_to}"
  # Cleanup.
  rm -rf "${tmp_build_dir}"
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

    tmp_build_dir="$(mktemp -d -t tmp_build_dir)"

    # Build binary wheel for arm64.
    _build_wheel_for_macos 11.0 arm64 "${tmp_build_dir}"
    arm64_whl="$(echo ${tmp_build_dir}/tink-*arm64.whl)"
    time python3 -m delocate.cmd.delocate_wheel \
      --require-archs arm64 -v "${arm64_whl}"

    # Build binary wheel for x86.
    _build_wheel_for_macos 10.9 x86_64 "${tmp_build_dir}"
    x86_64_whl="$(echo ${tmp_build_dir}/tink-*x86_64.whl)"
    time python3 -m delocate.cmd.delocate_wheel \
      --require-archs x86_64 -v "${x86_64_whl}"

    _create_universal2_macos_wheel "${arm64_whl}" "${x86_64_whl}" "release"

    rm -rf "${tmp_build_dir}"
    ls -l release
  done
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
