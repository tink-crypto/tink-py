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
  chmod +x "${KOKORO_GFILE_DIR}/use_bazel.sh"
  "${KOKORO_GFILE_DIR}/use_bazel.sh" "$(cat .bazelversion)"
fi

: "${TINK_BASE_DIR:=$(cd .. && pwd)}"

# Check for dependencies in TINK_BASE_DIR. Any that aren't present will be
# downloaded.
readonly GITHUB_ORG="https://github.com/tink-crypto"
./kokoro/testutils/fetch_git_repo_if_not_present.sh "${TINK_BASE_DIR}" \
  "${GITHUB_ORG}/tink-cc" "${GITHUB_ORG}/tink-cc-awskms" \
  "${GITHUB_ORG}/tink-cc-gcpkms"

cp "examples/WORKSPACE" "examples/WORKSPACE.bak"

./kokoro/testutils/replace_http_archive_with_local_repository.py \
  -f "examples/WORKSPACE" -t "${TINK_BASE_DIR}"

# Install protobuf pip packages.

# TODO(b/253216420): Investigate why this needs to be installed instead on
# MacOS, but not on GCP Ubuntu.
pip3 install protobuf==3.20.1 --user

# All test targets except manual and *test_package ones.
readonly MANUAL_TARGETS="$(cd examples \
  && bazel query \
    'kind(.*_test, ...) except attr(tags, manual, ...) except filter(.*test_package, ...)')"
IFS=' ' read -a MANUAL_TARGETS_ARRAY \
  <<< "$(tr '\n' ' ' <<< "${MANUAL_TARGETS}")"
readonly MANUAL_TARGETS_ARRAY

./kokoro/testutils/run_bazel_tests.sh -m "examples" "${MANUAL_TARGETS_ARRAY[@]}"

mv "examples/WORKSPACE.bak" "examples/WORKSPACE"
