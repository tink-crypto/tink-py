:: Copyright 2024 Google LLC
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

SET TINK_PYTHON_ROOT_PATH=%cd%

CALL :InstallTink || GOTO :Error
CALL :RunTests || GOTO :Error
GOTO :Exit

:InstallTink
  ECHO Install started at %TIME%
  choco install -y --no-progress protoc --version=25.2.0 || EXIT /B %errorlevel%
  python -m pip install --upgrade pip
  python -m pip install --upgrade setuptools
  python -m pip install --require-hashes --no-deps ^
    -r requirements.txt || EXIT /B %errorlevel%
  python -m pip install --no-deps . || EXIT /B %errorlevel%
  ECHO Install completed at %TIME%
  EXIT /B 0

:RunTests
  ECHO Tests started at %TIME%
  SET RET_VALUE=0
  FOR /F %%x in ('DIR /s/b tink\*_test.py') DO (
    ECHO %%x | FINDSTR "integration pybind" 1>nul
    IF errorlevel 1 (
      python %%x
      IF errorlevel 1 SET RET_VALUE=1
    ) ELSE (
      ECHO "Skip test file %%x"
    )
  )
  ECHO Test completed at %TIME%
  EXIT /B %RET_VALUE%

:Error
  EXIT /B 1

:Exit
  EXIT /B 0
