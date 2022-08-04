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

# The user may specify TINK_EXAMPLES_PYTHON_DEPS_ROOT as the location where
# finding the dependencies of tink-py.

set -euo pipefail

# If we are running on Kokoro cd into the repository.
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  cd "${KOKORO_ARTIFACTS_DIR}/git/tink_py"
  use_bazel.sh "$(cat .bazelversion)"
fi

# Note: When running on the Kokoro CI, we expect these folders to exist:
#
#  ${KOKORO_ARTIFACTS_DIR}/git/tink_cc
#  ${KOKORO_ARTIFACTS_DIR}/git/tink_cc_awskms
#  ${KOKORO_ARTIFACTS_DIR}/git/tink_cc_gcpkms
#  ${KOKORO_ARTIFACTS_DIR}/git/tink_py
#
# If this is not the case, we are using this script locally for a manual one-off
# test running it from the root of a local copy of the tink-py repository.
: "${TINK_BASE_DIR:=$(pwd)/..}"

readonly DEPENDENCIES=(
  tink-cc
  tink-cc-awskms
  tink-cc-gcpkms
)

# If dependencies of tink-py aren't in TINK_BASE_DIR we fetch them from GitHub.
for dependency in "${DEPENDENCIES[@]}"; do
  relative_path="$(echo ${dependency} | sed 's~-~_~g')"
  if [[ ! -d "${TINK_BASE_DIR}/${relative_path}" ]]; then
    git clone https://github.com/tink-crypto/"${dependency}".git \
      "${TINK_BASE_DIR}/${relative_path}"
  fi
done

echo "Using Tink from ${TINK_BASE_DIR}/tink_cc"
echo "Using Tink from ${TINK_BASE_DIR}/tink_cc_awskms"
echo "Using Tink from ${TINK_BASE_DIR}/tink_cc_gcpkms"

# Sourcing required to update callers environment.
source ./kokoro/testutils/install_python3.sh
source ./kokoro/testutils/install_tink_via_pip.sh \
  "${TINK_BASE_DIR}/tink_py"
./kokoro/testutils/copy_credentials.sh "examples/testdata"

# Targets tagged as "manual" that require setting GCP credentials.
MANUAL_EXAMPLE_PYTHON_TARGETS=()
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  MANUAL_EXAMPLE_PYTHON_TARGETS=(
    "//gcs:gcs_envelope_aead_test_package"
    "//gcs:gcs_envelope_aead_test"
    "//envelope_aead:envelope_test_package"
    "//envelope_aead:envelope_test"
    "//encrypted_keyset:encrypted_keyset_test_package"
    "//encrypted_keyset:encrypted_keyset_test"
  )
fi
readonly MANUAL_EXAMPLE_PYTHON_TARGETS

cp "examples/WORKSPACE" "examples/WORKSPACE.bak"

./kokoro/testutils/replace_http_archive_with_local_repository.py \
  -f "examples/WORKSPACE" \
  -t "${TINK_BASE_DIR}"

./kokoro/testutils/run_bazel_tests.sh \
  "examples" \
  "${MANUAL_EXAMPLE_PYTHON_TARGETS[@]}"

mv "examples/WORKSPACE.bak" "examples/WORKSPACE"
