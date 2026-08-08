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
# Tests for the Cloud KMS digital signature example.
#############################################################################

CLI="$1"
KEY_NAME="$2"
CRED_FILE="$3"
PUB_KEY_FILE="$4"

# Root certificates for GRPC.
# Reference:
#   https://github.com/grpc/grpc/blob/master/doc/environment_variables.md
export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH="${TEST_SRCDIR}/google_root_pem/file/downloaded"

DATA_FILE="$TEST_TMPDIR/example_data.txt"
SIGNATURE_FILE="$TEST_TMPDIR/expected_signature.hex"

echo "This is some data to be signed." > "${DATA_FILE}"

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

print_test "sign"

# Run signing.
test_command "${CLI}" --mode sign --key_name "${KEY_NAME}" \
  --gcp_credential_path "${CRED_FILE}" \
  --data_path "${DATA_FILE}" --signature_path "${SIGNATURE_FILE}"

if (( TEST_STATUS == 0 )); then
  echo "+++ Success: data was signed."
else
  echo "--- Failure: could not sign data."
  exit 1
fi

#############################################################################

print_test "verify"

# Run verification.
test_command "${CLI}" --mode verify --key_name "${KEY_NAME}" \
  --gcp_credential_path "${CRED_FILE}" \
  --data_path "${DATA_FILE}" --signature_path "${SIGNATURE_FILE}"

if (( TEST_STATUS == 0 )); then
  echo "+++ Success: signature was verified."
else
  echo "--- Failure: could not verify signature."
  exit 1
fi

#############################################################################

print_test "verify_fails_with_modified_data"

# Verification of a modified message must fail.
MODIFIED_DATA_FILE="$TEST_TMPDIR/modified_data.txt"
echo "This is some modified data." > "${MODIFIED_DATA_FILE}"

test_command "${CLI}" --mode verify --key_name "${KEY_NAME}" \
  --gcp_credential_path "${CRED_FILE}" \
  --data_path "${MODIFIED_DATA_FILE}" --signature_path "${SIGNATURE_FILE}"

if (( TEST_STATUS == 1 )); then
  echo "+++ Success: verification failed as expected for modified data."
else
  echo "--- Failure: verification of modified data did not fail."
  exit 1
fi

#############################################################################

print_test "verify-offline"

test_command "${CLI}" --mode verify_offline --public_key_path "${PUB_KEY_FILE}" \
  --algorithm "EC_SIGN_P256_SHA256" \
  --data_path "${DATA_FILE}" --signature_path "${SIGNATURE_FILE}"

if (( TEST_STATUS == 0 )); then
  echo "+++ Success: signature verified offline."
else
  echo "--- Failure: could not verify signature offline."
  exit 1
fi

#############################################################################

print_test "verify_offline_fails_with_modified_data"

test_command "${CLI}" --mode verify_offline --public_key_path "${PUB_KEY_FILE}" \
  --algorithm "EC_SIGN_P256_SHA256" \
  --data_path "${MODIFIED_DATA_FILE}" --signature_path "${SIGNATURE_FILE}"

if (( TEST_STATUS == 1 )); then
  echo "+++ Success: offline verification failed as expected for modified data."
else
  echo "--- Failure: offline verification of modified data did not fail."
  exit 1
fi
