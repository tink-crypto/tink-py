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

# Installs pyenv.
#
# Usage: source kokoro/testutils/install_pyenv.sh

set -eou pipefail

readonly PYENV_INSTALL_VERSION="2.8.15"
# PYENV_SHA256 was calculated with:
# curl -LsS https://github.com/pyenv/pyenv/archive/refs/tags/v2.8.15.zip | sha256sum
readonly PYENV_SHA256="280b5b4c3bf202a8d22de031f29488ab1e287ada353baaee4fbac52577f903c8"
readonly PYENV_URL="https://github.com/pyenv/pyenv/archive/refs/tags/v${PYENV_INSTALL_VERSION}.zip"
# The pyenv pre-installed on Kokoro macOS images is too old to know recent
# Python versions, so we install a pinned one. The version is part of the path
# so that an installation of a different pyenv version is never reused.
export PYENV_ROOT="/tmp/pyenv-${PYENV_INSTALL_VERSION}"

if [[ ! -d "${PYENV_ROOT}" ]]; then
  (
    cd "$(mktemp -d -t pyenv.XXXXXX)"
    curl -LsS "${PYENV_URL}" -o pyenv.zip
    echo "${PYENV_SHA256}  pyenv.zip" | shasum -a 256 -c
    # The archive contains a single pyenv-<version> folder. Move it in place
    # only once it is fully extracted.
    unzip -q pyenv.zip
    mv "pyenv-${PYENV_INSTALL_VERSION}" "${PYENV_ROOT}"
  )
fi

export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init -)"
pyenv --version
