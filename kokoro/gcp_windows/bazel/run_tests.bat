:: Copyright 2023 Google LLC
::
:: Licensed under the Apache License, Version 2.0 (the "License");
:: you may not use this file except in compliance with the License.
:: You may obtain a copy of the License at
::
::      http://www.apache.org/licenses/LICENSE-2.0
::
:: Unless required by applicable law or agreed to in writing, software
:: distributed under the License is distributed on an "AS IS" BASIS,
:: WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
:: See the License for the specific language governing permissions and
:: limitations under the License.
SETLOCAL ENABLEDELAYEDEXPANSION

IF EXIST %KOKORO_ARTIFACTS_DIR%\git\tink_py (
  SET WORKSPACE_DIR=%KOKORO_ARTIFACTS_DIR%\git\tink_py
) ELSE IF EXIST %KOKORO_ARTIFACTS_DIR%\github\tink_py (
  SET WORKSPACE_DIR=%KOKORO_ARTIFACTS_DIR%\github\tink_py
)

CD !WORKSPACE_DIR!
IF %errorlevel% neq 0 EXIT /B 1

ECHO Build started at %TIME%
: We have to set PYTHON_BIN_PATH because pybind11_bazel tries `which python3`
: [1], but there is no python3.exe in our test config (the bin is python.exe).
: [1] https://github.com/pybind/pybind11_bazel/blob/8889d39b2b925b2a47519ae09402a96f00ccf2b4/python_configure.bzl#L169C62-L169C62
: TODO(b/217559572): Investigate if this is intended (and fix our config) or a
: bug.
bazel --output_base=C:\O build ^
  --action_env PYTHON_BIN_PATH=C:/Python38/python.exe ^
  --action_env PYTHON_LIB_PATH=C:/Python38/libs -- ...
IF %errorlevel% neq 0 EXIT /B 1
ECHO Build completed at %TIME%

ECHO Test started at %TIME%
bazel --output_base=C:\O test --strategy=TestRunner=standalone ^
  --test_output=errors ^
  --action_env PYTHON_BIN_PATH=C:/Python38/python.exe ^
  --action_env PYTHON_LIB_PATH=C:/Python38/libs -- ...
IF %errorlevel% neq 0 EXIT /B 1
ECHO Test completed at %TIME%

EXIT /B 0
