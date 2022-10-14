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

# Fetches a list of deps if not already present in the given destination folder.
#
# This is useful for manual local tests.

set -euo pipefail

readonly DESTINATION_PATH="$1"
shift 1
readonly GIT_REPOS=("$@")

for git_repo in "${GIT_REPOS[@]}"; do
  repo_folder_name="$(echo ${git_repo##*/} | sed 's#-#_#g')"
  repo_full_path="${DESTINATION_PATH}/${repo_folder_name}"
  if [[ ! -d "${repo_full_path}" ]]; then
    git clone "${git_repo}.git" "${repo_full_path}"
  fi
done
