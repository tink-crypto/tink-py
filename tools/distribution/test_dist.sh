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

# Tests all the source and binary distributions in a given folder.

# Unique hex string of length 20
echo "================================================================================"
echo "Tink Script ID: 8159caa490bc1fdb066a (to quickly find the script from logs)"
echo "================================================================================"

set -euox pipefail

readonly PLATFORM="$(uname | tr '[:upper:]' '[:lower:]')"
readonly GCS_URL="https://storage.googleapis.com"
export TINK_PYTHON_ROOT_PATH="${PWD}"

usage() {
  cat <<EOF
Usage:  $0 [-c Bazel cache name] <sdists/bdists dir>
  -c: [Optional] Bazel cache to use; credentials are expected to be in a
      cache_key file.
  -h: Help. Print this usage information.
EOF
  exit 1
}

RELEASE_ARTIFACTS_DIR=
BAZEL_CACHE_NAME=

parse_args() {
  # Parse options.
  while getopts "hc:" opt; do
    case "${opt}" in
      c) BAZEL_CACHE_NAME="${OPTARG}" ;;
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  readonly BAZEL_CACHE_NAME
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
    echo "InvalidArgumentError: Invalid dist path '${dist}'" >&2
    exit 1
  fi
  local extras="all"
  local test_filters=( -not -path "*cc/pybind*" )
  local -r gil_disabled="$(python3 -c \
    'import sysconfig; print(sysconfig.get_config_var("Py_GIL_DISABLED") or 0)')"
  if [[ "${gil_disabled}" == "1" ]]; then
    # grpcio, which the gcpkms extra needs, has no free-threaded wheels yet.
    extras="awskms,hcvault"
    test_filters+=( -not -path "*integration/gcpkms*" )
  fi
  python3 -m pip install "${dist}[${extras}]"
  find tink/ "${test_filters[@]}" -type f -name "*_test.py" -print0 \
    | xargs -0 -n1 python3
}

enable_py_version() {
  # A partial version number (e.g. "3.10"), with a "t" suffix for a
  # free-threaded build (e.g. "3.15t").
  local -r partial_version="$1"
  if [[ -z "${partial_version}" ]]; then
    echo "InvalidArgumentError: Partial version must be specified" >&2
    exit 1
  fi
  local minor_version="${partial_version}"
  local flavor=""
  if [[ "${partial_version}" == *t ]]; then
    minor_version="${partial_version%t}"
    flavor="t"
  fi
  # Matches "3.10.x" for "3.10", and "3.15.xt" (but not "3.15.x") for "3.15t".
  local -r version_regex="^${minor_version//./\\.}\.[0-9]+${flavor}\$"

  # The latest installed Python version that matches the partial version number
  # (e.g. "3.10.x").
  local version="$(pyenv versions --bare | grep -E "${version_regex}" \
    | tail -1)"
  if [[ -z "${version}" ]]; then
    # Install the latest available non-dev version.
    version="$(pyenv install --list | xargs -n1 | grep -E "${version_regex}" \
      | tail -1)"
    pyenv install "${version}"
  fi
  readonly version
  # Set current Python version via environment variable.
  pyenv shell "${version}"
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

  if [[ -n "${BAZEL_CACHE_NAME:-}" ]]; then
    export TINK_PYTHON_BAZEL_REMOTE_CACHE_GCS_BUCKET_URL="${GCS_URL}/${BAZEL_CACHE_NAME}"
    export TINK_PYTHON_BAZEL_REMOTE_CACHE_SERVICE_KEY_PATH="$(realpath cache_key)"
  fi

  eval "$(pyenv init -)"

  for dist in "${RELEASE_ARTIFACTS_DIR}/tink-"*; do
    if ! is_sdist "${dist}"; then
      # This is a binary wheel; extract and enable the corresponding Python
      # version from its ABI tag (e.g. "3.15" for cp315, "3.15t" for cp315t).
      local python_version="$(basename "${dist}" \
        | sed -E 's/^tink-[^-]+-cp3[0-9]+-cp3([0-9]+t?)-.*$/3.\1/')"
      enable_py_version "${python_version}"
    fi
    # Update environment.
    python3 -m pip install --require-hashes -r \
      "${TINK_PYTHON_ROOT_PATH}/tools/distribution/requirements.txt"
    install_dist_and_run_tests "${dist}"
  done
}

main "$@"
