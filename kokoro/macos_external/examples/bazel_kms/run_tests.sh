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

# The user may specify TINK_BASE_DIR as the location where finding the
# dependencies of tink-py.

set -euo pipefail

# If we are running on Kokoro cd into the repository.
if [[ -n "${KOKORO_ROOT:-}" ]]; then
  TINK_BASE_DIR="$(echo "${KOKORO_ARTIFACTS_DIR}"/git*)"
  cd "${TINK_BASE_DIR}/tink_py"
  use_bazel.sh "$(cat .bazelversion)"
fi

: "${TINK_BASE_DIR:=$(cd .. && pwd)}"

# Check for dependencies in TINK_BASE_DIR. Any that aren't present will be
# downloaded.
readonly GITHUB_ORG="https://github.com/tink-crypto"
./kokoro/testutils/fetch_git_repo_if_not_present.sh "${TINK_BASE_DIR}" \
  "${GITHUB_ORG}/tink-cc" "${GITHUB_ORG}/tink-cc-awskms" \
  "${GITHUB_ORG}/tink-cc-gcpkms"

# Sourcing required to update callers environment.
source ./kokoro/testutils/install_tink_via_pip.sh "${TINK_BASE_DIR}/tink_py"
./kokoro/testutils/copy_credentials.sh "examples/testdata" "gcp"

readonly MANUAL_EXAMPLE_PYTHON_TARGETS=(
  "//gcs:gcs_envelope_aead_test_package"
  "//gcs:gcs_envelope_aead_test"
  "//envelope_aead:envelope_test_package"
  "//envelope_aead:envelope_test"
  "//encrypted_keyset:encrypted_keyset_test_package"
  "//encrypted_keyset:encrypted_keyset_test"
)

cp "examples/WORKSPACE" "examples/WORKSPACE.bak"

./kokoro/testutils/replace_http_archive_with_local_repository.py \
  -f "examples/WORKSPACE" \
  -t "${TINK_BASE_DIR}"

./kokoro/testutils/run_bazel_tests.sh -m "examples" \
  "${MANUAL_EXAMPLE_PYTHON_TARGETS[@]}"

mv "examples/WORKSPACE.bak" "examples/WORKSPACE"
