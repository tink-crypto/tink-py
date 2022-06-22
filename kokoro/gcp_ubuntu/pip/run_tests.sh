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


# The user may specify TINK_BASE_DIR for setting a local copy of Tink to use
# when running the script locally.

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

# If dependencies of tink-py aren't in TINK_BASE_DIR we fetch them from GitHub.
if [[ ! -d "${TINK_BASE_DIR}/tink_cc" ]]; then
  git clone https://github.com/tink-crypto/tink-cc.git \
    "${TINK_BASE_DIR}/tink_cc"
fi

if [[ ! -d "${TINK_BASE_DIR}/tink_cc_awskms" ]]; then
  git clone https://github.com/tink-crypto/tink-cc-awskms.git \
    "${TINK_BASE_DIR}/tink_cc_awskms"
fi

if [[ ! -d "${TINK_BASE_DIR}/tink_cc_gcpkms" ]]; then
  git clone https://github.com/tink-crypto/tink-cc-gcpkms.git \
    "${TINK_BASE_DIR}/tink_cc_gcpkms"
fi

./kokoro/testutils/copy_credentials.sh "testdata"
# Sourcing required to update callers environment.
source ./kokoro/testutils/install_python3.sh
source ./kokoro/testutils/install_protoc.sh
source ./kokoro/testutils/install_tink_via_pip.sh "$(pwd)"

# testing/helper.py will look for testdata in TINK_PYTHON_ROOT_PATH/testdata.
export TINK_PYTHON_ROOT_PATH="$(pwd)"
# Run Python tests directly so the package is used.
# We exclude tests in tink/cc/pybind: they are implementation details and may
# depend on a testonly shared object.
find tink/ -not -path "*cc/pybind*" -type f -name "*_test.py" -print0 \
  | xargs -0 -n1 python3

# Generate release of the pip package and test it
# TODO(b/233570181): Add support for creating releases.
# ./tools/distribution/create_release.sh
