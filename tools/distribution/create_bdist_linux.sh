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
echo "Tink Script ID: c7786ee77f797a059671 (to quickly find the script from logs)"
echo "================================================================================"

set -eEuox pipefail

# This script creates binary wheels for Tink Python for Linux. It must be run
# from the Tink Python root folder, inside the Tink manylinux image
# (manylinux_2_28), which has the tools required to build Tink Python.

readonly GCS_URL="https://storage.googleapis.com"

# The following assoicative array contains:
#   ["<Python version>"]="<python tag>-<abi tag>"
# where:
#   <Python version> = language version "<major>.<minor>", with a "t" suffix
#       for a free-threaded build, e.g. "3.15t"
#   <python tag>, <abi tag> = as defined at
#       https://packaging.python.org/en/latest/specifications/, e.g.
#       "cp<major><minor>-cp<major><minor>"
declare -A PYTHON_VERSIONS
PYTHON_VERSIONS["3.11"]="cp311-cp311"
PYTHON_VERSIONS["3.12"]="cp312-cp312"
PYTHON_VERSIONS["3.13"]="cp313-cp313"
PYTHON_VERSIONS["3.14"]="cp314-cp314"
PYTHON_VERSIONS["3.15"]="cp315-cp315"
PYTHON_VERSIONS["3.15t"]="cp315-cp315t"
readonly -A PYTHON_VERSIONS

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
# Builds a binary wheel for each Python version in PYTHON_VERSIONS and repairs
# the wheels into manylinux wheels, which are stored in the "release" folder.
#
# This function must be called from within the Tink Python's root folder.
#
# Globals:
#   PYTHON_VERSIONS
# Arguments:
#   None
#######################################
build_linux_binary_wheels() {
  local v
  for v in "${!PYTHON_VERSIONS[@]}"; do
    (
      # Executing in a subshell to make the PATH modification temporary.
      # This makes shure that `which python3 ==
      # /opt/python/${PYTHON_VERSIONS[$v]}/bin/python3`, which is a symlink of
      # `/opt/python/${PYTHON_VERSIONS[$v]}/bin/python${v}`. This should allow
      # pybind11_bazel to pick up the correct Python binary [1].
      #
      # [1] https://github.com/pybind/pybind11_bazel/blob/fc56ce8a8b51e3dd941139d329b63ccfea1d304b/python_configure.bzl#L434
      export PATH="/opt/python/${PYTHON_VERSIONS[$v]}/bin:${PATH}"
      python3 -m pip wheel .
    )
  done

  # Repair wheels to convert them from linux to manylinux.
  local wheel
  for wheel in ./tink*.whl; do
    auditwheel repair "${wheel}" -w release
  done
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
#   PYTHON_VERSIONS
# Arguments:
#   None
#######################################
create_bdist_for_linux() {
  echo "### Building Linux binary wheels ###"

  export TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION="${TINK_VERSION}"
  if [[ -n "${BAZEL_CACHE_NAME:-}" ]]; then
    export TINK_PYTHON_BAZEL_REMOTE_CACHE_GCS_BUCKET_URL="${GCS_URL}/${BAZEL_CACHE_NAME}"
    export TINK_PYTHON_BAZEL_REMOTE_CACHE_SERVICE_KEY_PATH="/tmp/cache_key"
  fi

  rm -rf release && mkdir -p release

  build_linux_binary_wheels
}

main() {
  parse_args "$@"

  local platform
  platform="$(uname | tr '[:upper:]' '[:lower:]')"
  readonly platform
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
