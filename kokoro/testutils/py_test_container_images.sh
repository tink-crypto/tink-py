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
readonly TINK_PY_BASE_IMAGE_HASH="1f401273d0efbf7cfe2bddc5ce374c94e5172677a432a635b5a10aa17e18c7a6"
readonly TINK_PY_BASE_IMAGE="$(_image_prefix)/${TINK_PY_BASE_IMAGE_NAME}@sha256:${TINK_PY_BASE_IMAGE_HASH}"

# Linux arm64 container image.
readonly TINK_PY_BASE_ARM64_IMAGE_NAME="linux-tink-py-base-arm64"
readonly TINK_PY_BASE_ARM64_IMAGE_HASH="7aa4beb17fb98adeb56c4c04dee396083238aa707cfb98335884d8d154996e53"
readonly TINK_PY_BASE_ARM64_IMAGE="$(_image_prefix)/${TINK_PY_BASE_ARM64_IMAGE_NAME}@sha256:${TINK_PY_BASE_ARM64_IMAGE_HASH}"

unset -f _image_prefix
