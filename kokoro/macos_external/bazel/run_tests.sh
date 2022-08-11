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

# The user may specify TINK_BASE_DIR for setting the base folder where the
# script should look for the dependencies of tink-py.

set -euo pipefail

# If we are running on Kokoro cd into the repository.
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  cd "${KOKORO_ARTIFACTS_DIR}/git/tink_py"
  use_bazel.sh "$(cat .bazelversion)"
fi

# Note: When running on the Kokoro CI, we expect these two folders to exist:
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

./kokoro/testutils/copy_credentials.sh "testdata" "all"
# Install protobuf pip packages.
pip3 install protobuf --user

TINK_PY_MANUAL_TARGETS=()
# These tests require valid credentials to access KMS services.
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  TINK_PY_MANUAL_TARGETS+=(
    "//tink/integration/awskms:_aws_kms_aead_test"
    "//tink/integration/gcpkms:_gcp_kms_aead_test"
  )
fi
readonly TINK_PY_MANUAL_TARGETS

cp "WORKSPACE" "WORKSPACE.bak"
./kokoro/testutils/replace_http_archive_with_local_repository.py \
  -f "WORKSPACE" \
  -t "${TINK_BASE_DIR}"
./kokoro/testutils/run_bazel_tests.sh . "${TINK_PY_MANUAL_TARGETS[@]}"
mv "WORKSPACE.bak" "WORKSPACE"
