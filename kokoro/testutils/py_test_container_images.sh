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
readonly TINK_PY_BASE_IMAGE_HASH="ef3e4ffcf8f722b13f774adceea7a3b5530f9982578d375f4ad3b497a99c0459"
readonly TINK_PY_BASE_IMAGE="$(_image_prefix)/${TINK_PY_BASE_IMAGE_NAME}@sha256:${TINK_PY_BASE_IMAGE_HASH}"

# Linux arm64 container image.
readonly TINK_PY_BASE_ARM64_IMAGE_NAME="linux-tink-py-base-arm64"
readonly TINK_PY_BASE_ARM64_IMAGE_HASH="c10dbba1d06429b6ea2d3934dbee7bf0daad51983d52235eee99d8b6c24cac51"
readonly TINK_PY_BASE_ARM64_IMAGE="$(_image_prefix)/${TINK_PY_BASE_ARM64_IMAGE_NAME}@sha256:${TINK_PY_BASE_ARM64_IMAGE_HASH}"

# Manylinux x86_64 container image.
readonly TINK_PY_MANYLINUX_IMAGE_NAME="linux-tink-py-manylinux"
readonly TINK_PY_MANYLINUX_IMAGE_HASH="febcfee809d1696a9778b4a01e4ac81fc561bbf89ee345864512d8625d0e3cee"
readonly TINK_PY_MANYLINUX_IMAGE="$(_image_prefix)/${TINK_PY_MANYLINUX_IMAGE_NAME}@sha256:${TINK_PY_MANYLINUX_IMAGE_HASH}"

# Manylinux arm64 container image.
readonly TINK_PY_MANYLINUX_ARM64_IMAGE_NAME="linux-tink-py-manylinux-arm64"
readonly TINK_PY_MANYLINUX_ARM64_IMAGE_HASH="428706bbb6237a2829da09b4cd7807d17f3b5fbb6ee409dfbcc9679b6e2eb6ff"
readonly TINK_PY_MANYLINUX_ARM64_IMAGE="$(_image_prefix)/${TINK_PY_MANYLINUX_ARM64_IMAGE_NAME}@sha256:${TINK_PY_MANYLINUX_ARM64_IMAGE_HASH}"

unset -f _image_prefix
