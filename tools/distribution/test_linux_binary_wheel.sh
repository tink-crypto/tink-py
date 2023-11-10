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

# Tests a given binary wheel. This script is meant to run on a manylinux
# container.

set -euo pipefail

readonly ARCH="$(uname -m)"

BINARY_WHEEL_FILE=
parse_args() {
  # Parse options.
  while getopts "h" opt; do
    case "${opt}" in
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  BINARY_WHEEL_FILE="$1"
  if [[ ! -f "${BINARY_WHEEL_FILE:-}" ]]; then
    echo "InvalidArgumentError: File '${BINARY_WHEEL_FILE:-}' does not exist"
    exit 1
  fi
  readonly BINARY_WHEEL_FILE
}

usage() {
  echo "Usage:  $0 <binary wheel>"
  echo "  -h: Help. Print this usage information."
  exit 1
}

get_python_and_abi() {
  local -r wheel_file="$1"
  # The Python tag and ABI are defined here
  # https://packaging.python.org/en/latest/specifications/. Examples are:
  #   - cp38-cp38
  #   - cp39-cp39
  #   - cp310-cp310
  #   - cp311-cp311
  echo "${wheel_file}" | grep -oEi 'cp[0-9]{2,}-cp[0-9]{2,}m?'
}

main() {
  parse_args "$@"

  # This link is required on CentOS, as curl used in the AWS SDK looks for the
  # certificates in this location. Removing this line will cause the AWS KMS
  # tests to fail.
  ln -s /etc/ssl/certs/ca-bundle.trust.crt /etc/ssl/certs/ca-certificates.crt

  local test_ignore_paths=( -not -path "*cc/pybind*" )
  if [[ "${ARCH}" == "aarch64" || "${ARCH}" == "arm64" ]]; then
    # gRPC doesn't seem compatible with libstdc++ present in
    # manylinux2014_aarch64 (see https://github.com/grpc/grpc/issues/33734).
    # TODO(b/291055539): Re-enable these tests when/after this is solved.
    test_ignore_paths+=( -not -path "*integration/gcpkms*")
  fi
  readonly test_ignore_paths

  local -r python_tag="$(get_python_and_abi "${BINARY_WHEEL_FILE}")"
  export PATH="${PATH}:/opt/python/${python_tag}/bin"
  export TINK_PYTHON_ROOT_PATH="${PWD}"
  # Required to fix https://github.com/pypa/manylinux/issues/357.
  export LD_LIBRARY_PATH="/usr/local/lib"

  python3 -m pip install --require-hashes --no-deps -r requirements_all.txt
  python3 -m pip install --no-deps --no-index "${BINARY_WHEEL_FILE}[all]"
  find tink/ "${test_ignore_paths[@]}" -type f -name "*_test.py" -print0 \
    | xargs -0 -n1 python3
}

main "$@"
