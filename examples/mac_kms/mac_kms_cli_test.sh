#!/bin/bash
# Copyright 2026 Google LLC
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

set -euo pipefail

#############################################################################
# Tests for the Cloud KMS MAC example.
#############################################################################

CLI="$1"
KEY_NAME="$2"
CRED_FILE="$3"

# Root certificates for GRPC.
# Reference:
#   https://github.com/grpc/grpc/blob/master/doc/environment_variables.md
export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="${TEST_SRCDIR}/google_root_pem/file/downloaded"

DATA_FILE="$TEST_TMPDIR/example_data.txt"
MAC_FILE="$TEST_TMPDIR/expected_mac.hex"

echo "This is some data to be authenticated." > "${DATA_FILE}"

#############################################################################

# A helper function for getting the return code of a command that may fail.
# Temporarily disables error safety and stores return value in ${TEST_STATUS}.
# Usage:
# % test_command somecommand some args
# % echo ${TEST_STATUS}
test_command() {
  set +e
  "$@"
  TEST_STATUS=$?
  set -e
}

print_test() {
  echo "+++ Starting test $1..."
}

#############################################################################

print_test "compute"

# Run MAC computation.
test_command "${CLI}" --mode compute --key_name "${KEY_NAME}" \
  --gcp_credential_path "${CRED_FILE}" \
  --data_path "${DATA_FILE}" --mac_path "${MAC_FILE}"

if (( TEST_STATUS == 0 )); then
  echo "+++ Success: MAC was computed."
else
  echo "--- Failure: could not compute MAC."
  exit 1
fi

#############################################################################

print_test "verify"

# Run MAC verification.
test_command "${CLI}" --mode verify --key_name "${KEY_NAME}" \
  --gcp_credential_path "${CRED_FILE}" \
  --data_path "${DATA_FILE}" --mac_path "${MAC_FILE}"

if (( TEST_STATUS == 0 )); then
  echo "+++ Success: MAC was verified."
else
  echo "--- Failure: could not verify MAC."
  exit 1
fi

#############################################################################

print_test "verify_fails_with_modified_data"

# Verification of a modified message must fail.
MODIFIED_DATA_FILE="$TEST_TMPDIR/modified_data.txt"
echo "This is some modified data." > "${MODIFIED_DATA_FILE}"

test_command "${CLI}" --mode verify --key_name "${KEY_NAME}" \
  --gcp_credential_path "${CRED_FILE}" \
  --data_path "${MODIFIED_DATA_FILE}" --mac_path "${MAC_FILE}"

if (( TEST_STATUS == 1 )); then
  echo "+++ Success: verification failed as expected for modified data."
else
  echo "--- Failure: verification of modified data did not fail."
  exit 1
fi
