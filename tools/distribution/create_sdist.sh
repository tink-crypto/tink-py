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

set -eEuox pipefail

readonly PLATFORM="$(uname | tr '[:upper:]' '[:lower:]')"

usage() {
  cat <<EOF
Usage:  $0 [-v <Python version to use>] [-t <release type (dev|release)>]
  -t: [Optional] Type of release; if "dev", the genereted sdist archive is named
     tink-<version from TINK_VERSION.txt>-dev0.tar.gz; if "release",
     tink-<version from TINK_VERSION.txt>.tar.gz (default=dev).
  -v: [Optional] Python version to use (default=3.10).
  -h: Help. Print this usage information.
EOF
  exit 1
}

PYTHON_VERSION="3.10"
RELEASE_TYPE="dev"
TINK_VERSION=

parse_args() {
  # Parse options.
  while getopts "hv:t:" opt; do
    case "${opt}" in
      v) PYTHON_VERSION="${OPTARG}" ;;
      t) RELEASE_TYPE="${OPTARG}" ;;
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  readonly PYTHON_VERSION
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

  eval "$(pyenv init -)"
  mkdir -p release

  # TODO(b/281635529): Use a container for a more hermetic testing environment.
  # The latest installed Python version that matches the partial version number
  # (e.g. "3.9.5"). This is needed because PYTHON_VERSION may be only
  # MAJOR.MINOR.
  local -r version="$(pyenv versions --bare | grep "${PYTHON_VERSION}" \
    | tail -1)"
  pyenv shell "${version}"
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
