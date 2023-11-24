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

_image_prefix() {
  local -r artifact_registry_url="us-docker.pkg.dev"
  local -r test_project="tink-test-infrastructure"
  local -r artifact_registry_repo="tink-ci-images"
  echo "${artifact_registry_url}/${test_project}/${artifact_registry_repo}"
}

# Images for tink-py testing.

# Linux x86_64 container image.
readonly TINK_PY_BASE_IMAGE_NAME="linux-tink-py-base"
readonly TINK_PY_BASE_IMAGE_HASH="905ce5a967ffb088453b501189c7fba9d3d4ff5fb4b209d6eac72e5c3dbe2752"
readonly TINK_PY_BASE_IMAGE="$(_image_prefix)/${TINK_PY_BASE_IMAGE_NAME}@sha256:${TINK_PY_BASE_IMAGE_HASH}"

# Linux arm64 container image.
readonly TINK_PY_BASE_ARM64_IMAGE_NAME="linux-tink-py-base-arm64"
readonly TINK_PY_BASE_ARM64_IMAGE_HASH="3a8569713397871c4d1d1690b777fcc189a66f23c84d07628cf7d65439e4fad8"
readonly TINK_PY_BASE_ARM64_IMAGE="$(_image_prefix)/${TINK_PY_BASE_ARM64_IMAGE_NAME}@sha256:${TINK_PY_BASE_ARM64_IMAGE_HASH}"

unset -f _image_prefix
