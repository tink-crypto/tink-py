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

# This script creates a source distribution for tink-py.
#
# https://packaging.python.org/en/latest/glossary/#term-Source-Distribution-or-sdist

# Unique hex string of length 20
echo "================================================================================"
echo "Tink Script ID: 97a8fcd3485efd909ebd (to quickly find the script from logs)"
echo "================================================================================"

set -eEuox pipefail

readonly PLATFORM="$(uname | tr '[:upper:]' '[:lower:]')"

usage() {
  cat <<EOF
Usage:  $0 [-t <release type (dev|release)>]
  -t: [Optional] Type of release; if "dev", the genereted sdist archive is named
     tink-<version from TINK_VERSION.txt>-dev0.tar.gz; if "release",
     tink-<version from TINK_VERSION.txt>.tar.gz (default=dev).
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

  TINK_VERSION="$(cat TINK_VERSION.txt)"
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

main() {
  echo "### Building and testing sdist ###"

  if [[ "${PLATFORM}" != "linux" ]]; then
    echo "ERROR: ${PLATFORM} is not a supported platform." >&2
    exit 1
  fi

  parse_args "$@"

  export TINK_PYTHON_ROOT_PATH="${PWD}"

  mkdir -p release

  readonly PYTHON_VERSION="3.11"
  eval "$(pyenv init -)"
  pyenv shell "${PYTHON_VERSION}"
  python3 --version

  # Update environment.
  python3 -m pip install --require-hashes -r \
    ./tools/distribution/requirements.txt

  export TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION="${TINK_VERSION}"

  # Build source distribution.
  python3 -m build -s
  local -r sdist_filename="tink-${TINK_VERSION}.tar.gz"
  cp "dist/${sdist_filename}" release/

  ls -l release/
}

main "$@"
