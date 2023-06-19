#!/bin/bash
# Copyright 2023 Google LLC
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

# Build, test and optionally release Tink Py binary and source distributions.
#
# The script uses the following env variables:
#
# - RELEASE_VERSION: Release version.
# - DO_MAKE_RELEASE: If true, actually perform the release; print commands
#   otherwise.
# - RELEASE_ON_PYPI: If true, use twine (https://pypi.org/project/twine) to
#   release tink-py binary and source distributions to PyPi (https://pypi.org).
# - RELEASE_ON_TEST_PYPI: If true, use twine (https://pypi.org/project/twine) to
#   release tink-py binary and source distributions to Test PyPi
#   (https://test.pypi.org).
#
# NOTE: Release on PyPi and Test PyPi are possible only when running on Kokoro.

# Fail if RELEASE_VERSION is not set.
if [[ -z "${RELEASE_VERSION:-}" ]]; then
  echo "ERROR: RELEASE_VERSION must be set" >&2
  exit 1
fi

IS_KOKORO="false"
if [[ -n "${KOKORO_ARTIFACTS_DIR:-}" ]]; then
  IS_KOKORO="true"
fi
readonly IS_KOKORO

# If not defined, default to /tmp.
: "${TMPDIR:=/tmp}"


# WARNING: Setting this environment variable to "true" will cause this script
# to actually perform a release.
: "${DO_MAKE_RELEASE:=false}"
if [[ ! "${DO_MAKE_RELEASE}" =~ ^(false|true)$ ]]; then
  echo "ERROR: DO_MAKE_RELEASE must be either \"true\" or \"false\"" >&2
  exit 1
fi

# WARNING: Setting this environment variable to "true" will cause this script
# to upload the generated wheels to PyPi.
: "${RELEASE_ON_PYPI:=false}"
if [[ ! "${RELEASE_ON_PYPI}" =~ ^(false|true)$ ]]; then
  echo "ERROR: RELEASE_ON_PYPI must be either \"true\" or \"false\"" >&2
  exit 1
fi

# WARNING: Setting this environment variable to "true" will cause this script
# to upload the generated wheels to Test PyPi.
: "${RELEASE_ON_TEST_PYPI:=false}"
if [[ ! "${RELEASE_ON_TEST_PYPI}" =~ ^(false|true)$ ]]; then
  echo "ERROR: RELEASE_ON_TEST_PYPI must be either \"true\" or \"false\"" >&2
  exit 1
fi

#######################################
# Runs a command if DO_MAKE_RELEASE is true.
#
# Args:
#   Command to execute.
# Globals:
#   DO_MAKE_RELEASE
#
#######################################
run_if_do_make_release() {
  if [[ "${DO_MAKE_RELEASE}" == "false" ]]; then
    echo "  *** Dry run, command not executed. ***"
    return 0
  fi
  # Actually run the command.
  "$@"
  return $?
}

main() {
  if [[ "${IS_KOKORO}" == "true" ]] ; then
    cd "${KOKORO_ARTIFACTS_DIR}"/git*/tink_py
  fi

  local -r version_value_in_version_file="$(grep ^TINK VERSION | cut -d\" -f2)"
  if [[ "${version_value_in_version_file}" != "${RELEASE_VERSION}" ]]; then
    echo "ERROR: Values in RELEASE_VERSION and VERSION file must coincide!" >&2
    echo "Found:" >&2
    echo "  RELEASE_VERSION=${RELEASE_VERSION}" >&2
    echo "  Value in VERSION file=${version_value_in_version_file}" >&2
    exit 1
  fi

  # Generate source distribution and binary wheels **without** editing the
  # WORSPACE file, and test them. The generated artifacts are going to be placed
  # in release/.
  ./tools/distribution/create_sdist.sh
  ./tools/distribution/create_bdist.sh


  if [[ "${IS_KOKORO}" == "true" ]]; then
    # See https://packaging.python.org/en/latest/specifications/pypirc/#using-a-pypi-token.
    # Tokens are injected by Kokoro.
    cat << EOF > "${HOME}/.pypirc"
[pypi]
username = __token__
password = ${TINK_PYPI_API_TOKEN}

[testpypi]
username = __token__
password = ${TINK_TEST_PYPI_API_TOKEN}
EOF
    run_if_do_make_release pip3 install --require-hashes \
      -r kokoro/release_requirements.txt
    if [[ "${RELEASE_ON_TEST_PYPI}" == "true" ]]; then
      run_if_do_make_release python3 -m twine upload --repository testpypi \
        --skip-existing release/*
    fi
    if [[ "${RELEASE_ON_PYPI}" == "true" ]]; then
      run_if_do_make_release python3 -m twine upload --skip-existing release/*
    fi
  fi
}

main "$@"
