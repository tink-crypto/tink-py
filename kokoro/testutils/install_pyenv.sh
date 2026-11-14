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

# This script installs a fresh pyenv and makes it the one in use.
#
# The pre-installed pyenv on Kokoro macOS 15 images is too old: it fails to
# compile Python 3.13, and Python 3.15 needs pyenv 2.8.9 or later. We install a
# fresh pyenv from GitHub into a temporary directory to get the latest patches
# and Python versions.
#
# NOTE: This script MUST be sourced to update the environment of the calling
# script.
#
# Usage:
#   source ./kokoro/testutils/install_pyenv.sh

export PYENV_ROOT="/tmp/pyenv"
if [ ! -d "${PYENV_ROOT}" ]; then
  git clone https://github.com/pyenv/pyenv.git "${PYENV_ROOT}"
fi
export PATH="${PYENV_ROOT}/bin:${PATH}"
