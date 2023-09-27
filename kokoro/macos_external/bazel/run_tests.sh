#!/bin/bash
# Copyright 2022 Google LLC
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

# Builds and tests tink-py and its examples using Bazel.
set -euo pipefail

BAZEL_CMD="bazel"
if command -v "bazelisk" &> /dev/null; then
  BAZEL_CMD="bazelisk"
fi
readonly BAZEL_CMD

# If we are running on Kokoro cd into the repository.
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  readonly TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_py"
fi

./kokoro/testutils/copy_credentials.sh "testdata" "all"
./kokoro/testutils/copy_credentials.sh "examples/testdata" "gcp"

# TODO(b/276277854) It is not clear why this is needed.
python3 -m pip install --require-hashes -r requirements_all.txt

./kokoro/testutils/run_bazel_tests.sh .
if [[ "${KOKORO_JOB_NAME:-}" =~ .*/bazel_kms/.* ]]; then
  readonly MANUAL_TARGETS="$(
    "${BAZEL_CMD}" query 'attr(tags, manual, kind(.*_test, ...))')"
  IFS=' ' read -a MANUAL_TARGETS_ARRAY <<< "$(tr '\n' ' ' \
    <<< "${MANUAL_TARGETS}")"
  readonly MANUAL_TARGETS_ARRAY
  ./kokoro/testutils/run_bazel_tests.sh -m . "${MANUAL_TARGETS_ARRAY[@]}"
fi

if [[ "${KOKORO_JOB_NAME:-}" =~ .*/bazel_kms/.* ]]; then
  # Run all the test targets excluding *test_package, including manual ones that
  # interact with a KMS.
  python3 -m pip install --require-hashes -r examples/requirements.txt

  TARGETS="$(cd examples && "${BAZEL_CMD}" query \
    'kind(.*_test, ...) except filter(.*test_package, ...)')"
else
  # Run all the test targets excluding *test_package, exclude manual ones.
  TARGETS="$(cd examples \
    && "${BAZEL_CMD}" query \
      'kind(.*_test, ...) except filter(.*test_package, ...) except attr(tags, manual, ...)')"
fi
readonly TARGETS

IFS=' ' read -a TARGETS_ARRAY <<< "$(tr '\n' ' ' <<< "${TARGETS}")"
readonly TARGETS_ARRAY

./kokoro/testutils/run_bazel_tests.sh -m "examples" "${TARGETS_ARRAY[@]}"
