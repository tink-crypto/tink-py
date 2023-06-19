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
Usage:  $0 [-l] [-v <Python version to use>]
  -l: [Optional] Build sdist against a local tink-cc located at ./..
  -v: [Optional] Python version to use (default=3.10).
  -h: Help. Print this usage information.
EOF
  exit 1
}

TINK_CC_USE_LOCAL="false"
PYTHON_VERSION="3.10"

parse_args() {
  # Parse options.
  while getopts "hlv:" opt; do
    case "${opt}" in
      l) TINK_CC_USE_LOCAL="true" ;;
      v) PYTHON_VERSION="${OPTARG}" ;;
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  readonly TINK_CC_USE_LOCAL
  readonly PYTHON_VERSION
}

cleanup() {
  mv WORKSPACE.bak WORKSPACE
}

main() {
  echo "### Building and testing sdist ###"

  if [[ "${PLATFORM}" != "linux" ]]; then
    echo "ERROR: ${PLATFORM} is not a supported platform." >&2
    exit 1
  fi

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

  if [[ "${TINK_CC_USE_LOCAL}" == "true" ]]; then
    export TINK_PYTHON_SETUPTOOLS_OVERRIDE_BASE_PATH="$(cd .. && pwd)"
  fi

  cp WORKSPACE WORKSPACE.bak

  trap cleanup EXIT

  local -r tink_version="$(grep ^TINK "${TINK_PYTHON_ROOT_PATH}/VERSION" \
    | awk '{gsub(/"/, "", $3); print $3}')"

  # Build source distribution.
  python3 setup.py sdist --owner=root --group=root
  local -r sdist_filename="tink-${tink_version}.tar.gz"
  cp "dist/${sdist_filename}" release/
  # Install Tink dependencies.
  python3 -m pip install --require-hashes -r requirements.txt
  # Install Tink from the generated sdist.
  python3 -m pip install --no-deps --no-index -v "release/${sdist_filename}"
  # Run unit tests.
  find tink/ -not -path "*cc/pybind*" -type f -name "*_test.py" -print0 \
    | xargs -0 -n1 python3
}

main "$@"
