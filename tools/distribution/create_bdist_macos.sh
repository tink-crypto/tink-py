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
echo "Tink Script ID: c132a38aeaf0d4e35ca0 (to quickly find the script from logs)"
echo "================================================================================"

set -eEuox pipefail

# This script creates binary wheels for Tink Python for Linux and macOS.

readonly GCS_URL="https://storage.googleapis.com"

readonly PYTHON_VERSIONS=( "3.11" "3.12" "3.13" "3.14" "3.15" )

export TINK_PYTHON_ROOT_PATH="${PWD}"

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

  local -r tmp_build_dir="$(mktemp -d -t universal2)"
  time python3 -m delocate.cmd.delocate_merge "${arm64_whl}" "${x86_whl}" \
    -w "${tmp_build_dir}"
  generated_whl="$(basename ${tmp_build_dir}/tink*universal2.whl)"
  mv "${tmp_build_dir}/${generated_whl}" "${out_dir}"
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
#   TINK_VERSION
#   BAZEL_CACHE_NAME
#   GCS_URL
#   TINK_PYTHON_ROOT_PATH
# Arguments:
#   None
#######################################
create_bdist_for_macos() {
  echo "### Building macOS binary wheels ###"

  source ./kokoro/testutils/install_pyenv.sh

  export TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION="${TINK_VERSION}"
  if [[ -n "${BAZEL_CACHE_NAME:-}" ]]; then
    export TINK_PYTHON_BAZEL_REMOTE_CACHE_GCS_BUCKET_URL="${GCS_URL}/${BAZEL_CACHE_NAME}"
    export TINK_PYTHON_BAZEL_REMOTE_CACHE_SERVICE_KEY_PATH="/tmp/cache_key"
  fi
  cat .bazelrc
  rm -rf release && mkdir -p release
  for python_version in "${PYTHON_VERSIONS[@]}"; do
    enable_py_version "${python_version}"

    tmp_build_dir="$(mktemp -d -t tmp_build_dir)"
    second_tmp_build_dir="$(mktemp -d -t second_tmp_build_dir)"
    # Build binary wheel for arm64.
    (
      export SETUP_PY_BAZEL_CONFIG="macos_arm64"
      export PLAT_NAME="macosx-11.0-arm64"
      time python3 -m pip wheel -w "${tmp_build_dir}" .
    )
    arm64_whl="$(basename ${tmp_build_dir}/tink-*arm64.whl)"
    # Use delocate to create a wheel which includes all dynamic libraries
    # needed. This might rename the wheel, so we recompute the name.
    time python3 -m delocate.cmd.delocate_wheel --require-archs arm64 \
      -v "${tmp_build_dir}/${arm64_whl}" -w "${second_tmp_build_dir}"
    arm64_whl="$(basename ${second_tmp_build_dir}/tink-*arm64.whl)"
    mv "${second_tmp_build_dir}/${arm64_whl}" "${tmp_build_dir}/"

    # Build binary wheel for x86.
    (
      export SETUP_PY_BAZEL_CONFIG="macos_x86_64"
      export PLAT_NAME="macosx-10.9-x86_64"
      time python3 -m pip wheel -w "${tmp_build_dir}" .
    )
    x86_64_whl="$(basename ${tmp_build_dir}/tink-*x86_64.whl)"
    # Use delocate to create a wheel which includes all dynamic libraries
    # needed. This might rename the wheel, so we recompute the name.
    time python3 -m delocate.cmd.delocate_wheel --require-archs x86_64 \
      -v "${tmp_build_dir}/${x86_64_whl}" -w "${second_tmp_build_dir}"
    x86_64_whl="$(basename ${second_tmp_build_dir}/tink-*x86_64.whl)"
    mv "${second_tmp_build_dir}/${x86_64_whl}" "${tmp_build_dir}/"

    # Use delocate to combine the two wheels into one (a universal2 wheel)
    _create_universal2_macos_wheel \
       "${tmp_build_dir}/${arm64_whl}" \
       "${tmp_build_dir}/${x86_64_whl}" "release"

    rm -rf "${tmp_build_dir}"
    ls -l release
  done
}

enable_py_version() {
  # A partial version number (e.g. "3.14").
  local -r partial_version="$1"
  if [[ -z "${partial_version}" ]]; then
    echo "InvalidArgumentError: Partial version must be specified" >&2
    exit 1
  fi
  pyenv install -s "${partial_version}"
  # Set current Python version via environment variable.
  pyenv shell "${partial_version}"
  # Update environment.
  python3 -m pip install --require-hashes -r \
    "${TINK_PYTHON_ROOT_PATH}/tools/distribution/requirements.txt"
}

main() {
  parse_args "$@"

  readonly platform="$(uname | tr '[:upper:]' '[:lower:]')"
  case "${platform}" in
    darwin)
      create_bdist_for_macos
      ;;
    *)
      echo "InvalidArgumentError: Unsupported platform ${platform}" >&2
      exit 1
      ;;
  esac
}

main "$@"
