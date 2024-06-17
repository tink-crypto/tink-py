#!/bin/bash
# Copyright 2024 Google LLC
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

# Test script for building tink-py and running tests with PiP.
#
# This script is assumed to be run from the root of the tink-py repository.

set -euo pipefail

readonly GCS_URL="https://storage.googleapis.com"

BAZEL_CMD="bazel"
if command -v "bazelisk" &> /dev/null; then
  BAZEL_CMD="bazelisk"
fi
readonly BAZEL_CMD

RUN_KMS_TESTS="false"

usage() {
  cat <<EOF
Usage:  $0 [-k] [-c Bazel cache name]
  -k: [Optional] If set, run KMS tests.
  -c: [Optional] Bazel cache to use; credentials are expected to be in a
      cache_key file.
  -h: Help. Print this usage information.
EOF
  exit 1
}

BAZEL_CACHE_NAME=

process_args() {
  # Parse options.
  while getopts "hkc:" opt; do
    case "${opt}" in
      k) RUN_KMS_TESTS="true" ;;
      c) BAZEL_CACHE_NAME="${OPTARG}" ;;
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  readonly RUN_KMS_TESTS
  readonly BAZEL_CACHE_NAME
}

process_args "$@"

# testing/helper.py will look for testdata in TINK_PYTHON_ROOT_PATH/testdata.
export TINK_PYTHON_ROOT_PATH="$(pwd)"
if [[ -n "${BAZEL_CACHE_NAME}" ]]; then
  export TINK_PYTHON_BAZEL_REMOTE_CACHE_GCS_BUCKET_URL="${GCS_URL}/${BAZEL_CACHE_NAME}"
  export TINK_PYTHON_BAZEL_REMOTE_CACHE_SERVICE_KEY_PATH="./cache_key"
fi

TEST_EXCLUDE=( -not -path "*cc/pybind*" )
if [[ "${RUN_KMS_TESTS}" == "true" ]]; then
  ./kokoro/testutils/install_tink_via_pip.sh -a "$(pwd)"
  source ./kokoro/testutils/install_vault.sh
  source ./kokoro/testutils/run_hcvault_test_server.sh
  vault write -f transit/keys/key-1
else
  ./kokoro/testutils/install_tink_via_pip.sh "$(pwd)"
  TEST_EXCLUDE+=( -not -path "*integration/*" )
fi
readonly TEST_EXCLUDE
find tink/ "${TEST_EXCLUDE}" -type f -name "*_test.py" -print0 \
  | xargs -0 -n1 python3

# Install requirements for examples.
python3 -m pip install --require-hashes --no-deps -r examples/requirements.txt
if [[ "${RUN_KMS_TESTS}" == "true" ]]; then
  # All *test_package targets, including manual ones.
  EXAMPLE_TARGETS="$(cd examples && "${BAZEL_CMD}" query \
    'filter(.*test_package, ...)')"
else
  # All non-manual *test_package targets.
  EXAMPLE_TARGETS="$(cd examples && "${BAZEL_CMD}" query \
    'filter(.*test_package, ...) except attr(tags, manual, ...)')"
fi
readonly EXAMPLE_TARGETS

IFS=' ' read -a EXAMPLE_TARGETS_ARRAY <<< "$(tr '\n' ' ' \
  <<< "${EXAMPLE_TARGETS}")"
readonly EXAMPLE_TARGETS_ARRAY

CACHE_FLAGS=()
if [[ -n "${BAZEL_CACHE_NAME:-}" ]]; then
  CACHE_FLAGS+=( -c "${BAZEL_CACHE_NAME}" )
fi
readonly CACHE_FLAGS

./kokoro/testutils/run_bazel_tests.sh -m "${CACHE_FLAGS[@]}" "examples" \
  "${EXAMPLE_TARGETS_ARRAY[@]}"
