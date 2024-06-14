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

# Test script for building tink-py and running tests with Bazel.
#
# This script is assumed to be run from the root of the tink-py repository.

set -euo pipefail

BAZEL_CMD="bazel"
if command -v "bazelisk" &> /dev/null; then
  BAZEL_CMD="bazelisk"
fi
readonly BAZEL_CMD

SHOULD_RUN_KMS_TESTS="false"

usage() {
  cat <<EOF
Usage:  $0 [-k] [-c Bazel cache name]
  -k: [Optional] If set, run KMS tests.
  -c: [Optional] Bazel cache to use; creadentials are expected to be in a
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
      k) SHOULD_RUN_KMS_TESTS="true" ;;
      c) BAZEL_CACHE_NAME="${OPTARG}" ;;
      *) usage ;;
    esac
  done
  shift $((OPTIND - 1))
  readonly SHOULD_RUN_KMS_TESTS
  readonly BAZEL_CACHE_NAME
}

process_args "$@"

CACHE_FLAGS=()
if [[ -n "${BAZEL_CACHE_NAME:-}" ]]; then
  CACHE_FLAGS+=( -c "${BAZEL_CACHE_NAME}" )
fi
readonly CACHE_FLAGS

# Build tink-py and run unit tests.
./kokoro/testutils/run_bazel_tests.sh "${CACHE_FLAGS[@]}" .

if [[ "${SHOULD_RUN_KMS_TESTS}" == "true" ]]; then
  source ./kokoro/testutils/install_vault.sh
  source ./kokoro/testutils/run_hcvault_test_server.sh
  vault write -f transit/keys/key-1

  readonly MANUAL_TARGETS="$(
    "${BAZEL_CMD}" query 'attr(tags, manual, kind(.*_test, ...))')"
  IFS=' ' read -a MANUAL_TARGETS_ARRAY <<< "$(tr '\n' ' ' \
    <<< "${MANUAL_TARGETS}")"
  readonly MANUAL_TARGETS_ARRAY

  # Make sure VAULT_ADDR and VAULT_TOKEN are available to the Bazel tests.
  MANUAL_TARGETS_TEST_ARGS="--test_env=VAULT_ADDR=${VAULT_ADDR}"
  MANUAL_TARGETS_TEST_ARGS+=",--test_env=VAULT_TOKEN=${VAULT_TOKEN}"
  readonly MANUAL_TARGETS_TEST_ARGS
  ./kokoro/testutils/run_bazel_tests.sh -m "${CACHE_FLAGS[@]}" \
    -t "${MANUAL_TARGETS_TEST_ARGS}" . "${MANUAL_TARGETS_ARRAY[@]}"
fi

# Fill EXAMPLE_TARGETS with the example tests targets to run.
if [[ "${SHOULD_RUN_KMS_TESTS}" == "true" ]]; then
  # Run all the test targets excluding *test_package, including manual ones that
  # interact with a KMS.

  #TODO(b/276277854) It is not clear why this is needed.
  python3 -m pip install --require-hashes --no-deps -r examples/requirements.txt

  EXAMPLE_TARGETS="$(cd examples && "${BAZEL_CMD}" query \
    'kind(.*_test, ...) except filter(.*test_package, ...)')"
else
  # Run all the test targets excluding *test_package, exclude manual ones.
  EXAMPLE_TARGETS="$(cd examples \
    && "${BAZEL_CMD}" query \
      'kind(.*_test, ...) except filter(.*test_package, ...) except attr(tags, manual, ...)')"
fi
readonly EXAMPLE_TARGETS

IFS=' ' read -a EXAMPLE_TARGETS_ARRAY <<< "$(tr '\n' ' ' \
  <<< "${EXAMPLE_TARGETS}")"
readonly EXAMPLE_TARGETS_ARRAY

./kokoro/testutils/run_bazel_tests.sh -m "${CACHE_FLAGS[@]}" "examples" \
  "${EXAMPLE_TARGETS_ARRAY[@]}"
