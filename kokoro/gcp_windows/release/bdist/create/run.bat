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

@REM Install protoc.
choco install -y --no-progress protoc --version=30.2.0
SET OLD_PATH=%PATH%

SET /p TINK_VERSION=<TINK_VERSION.txt
ECHO %KOKORO_JOB_NAME% | FINDSTR "github" | FINDSTR "release"
IF %errorlevel% NEQ 0 (
  SET TINK_VERSION=%TINK_VERSION%.dev0
)

IF NOT "%TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET%"=="" (
  SET TINK_PYTHON_BAZEL_REMOTE_CACHE_GCS_BUCKET_URL=https://storage.googleapis.com/%TINK_REMOTE_BAZEL_CACHE_GCS_BUCKET%/bazel/windows_tink_py
  SET TINK_PYTHON_BAZEL_REMOTE_CACHE_SERVICE_KEY_PATH=%TINK_REMOTE_BAZEL_CACHE_SERVICE_KEY%
)

SET TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION=%TINK_VERSION%
SET TINK_PYTHON_ROOT_PATH=%cd%

SET OUT_WHEEL=tink-%TINK_VERSION%-cp39-cp39-win_amd64.whl
CALL :BuildAndInstallWheel "3.9" || GOTO :Error
CALL :RunTests "3.9" || GOTO :Error

SET OUT_WHEEL=tink-%TINK_VERSION%-cp310-cp310-win_amd64.whl
CALL :BuildAndInstallWheel "3.10" || GOTO :Error
CALL :RunTests "3.10" || GOTO :Error

SET OUT_WHEEL=tink-%TINK_VERSION%-cp311-cp311-win_amd64.whl
CALL :BuildAndInstallWheel "3.11" || GOTO :Error
CALL :RunTests "3.11" || GOTO :Error

SET OUT_WHEEL=tink-%TINK_VERSION%-cp312-cp312-win_amd64.whl
CALL :BuildAndInstallWheel "3.12" || GOTO :Error
CALL :RunTests "3.12" || GOTO :Error

SET OUT_WHEEL=tink-%TINK_VERSION%-cp313-cp313-win_amd64.whl
CALL :BuildAndInstallWheel "3.13" || GOTO :Error
CALL :RunTests "3.13" || GOTO :Error

GOTO :End

@REM Builds repairs and installs the binary wheel, and places it in release/.
:BuildAndInstallWheel
  py -%~1 --version
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  py -%~1 -m pip install --no-deps --require-hashes -r tools\distribution\requirements.txt
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  py -%~1 -m pip install --no-deps --require-hashes -r requirements.txt
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  py -%~1 -m pip install delvewheel
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  py -%~1 -m pip wheel .
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  py -%~1 -m delvewheel repair %OUT_WHEEL% -w release
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  py -%~1 -m pip install --no-deps release/%OUT_WHEEL%
  EXIT /B %errorlevel%

:RunTests
  SET RET_VALUE=0
  FOR /F %%x in ('DIR /s/b tink\*_test.py') DO (
    ECHO %%x | FINDSTR "integration pybind" 1>nul
      IF errorlevel 1 (
        py -%~1 %%x
        IF errorlevel 1 SET RET_VALUE=1
      ) ELSE (
        ECHO "Skip test file %%x"
      )
    )
  EXIT /B %RET_VALUE%

:Error
  EXIT /B 1

:End
  EXIT /B 0

