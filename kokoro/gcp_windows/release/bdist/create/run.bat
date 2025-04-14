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
choco install -y --no-progress protoc --version=25.2.0
SET OLD_PATH=%PATH%

SET /p TINK_VERSION=<VERSION
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

CALL :UsePython "3.9.13" "39" || GOTO :Error
CALL :BuildAndInstallWheel || GOTO :Error
CALL :RunTests || GOTO :Error

CALL :UsePython "3.10.11" "310" || GOTO :Error
CALL :BuildAndInstallWheel || GOTO :Error
CALL :RunTests || GOTO :Error

CALL :UsePython "3.11.9" "311" || GOTO :Error
CALL :BuildAndInstallWheel || GOTO :Error
CALL :RunTests || GOTO :Error

CALL :UsePython "3.12.3" "312" || GOTO :Error
CALL :BuildAndInstallWheel || GOTO :Error
CALL :RunTests || GOTO :Error

GOTO :End

@REM Installs Python at the given version and sets the needed env. variables.
@REM
@REM Args:
@REM    version: <MAJOR>.<MINOR>.<PATCH>
@REM    cp: <MAJOR><MINOR>
@REM
@REM TODO(b/265261481): Derive cp from version.
:UsePython
  choco install -my --no-progress --allow-downgrade python --version=%~1%
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  SET PATH=C:\Python%~2\;C:\Python%~2\Scripts;%OLD_PATH%
  python -m pip install --no-deps --require-hashes -r ^
    tools\distribution\requirements.txt
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  python -m pip install --no-deps --require-hashes -r requirements.txt
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  python -m pip install --upgrade delvewheel
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  SET OUT_WHEEL=tink-%TINK_VERSION%-cp%~2-cp%~2-win_amd64.whl
  EXIT /B 0

@REM Builds repairs and installs the binary wheel, and places it in release/.
:BuildAndInstallWheel
  python -m pip wheel .
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  python -m delvewheel repair %OUT_WHEEL% -w release
  IF %errorlevel% neq 0 EXIT /B %errorlevel%

  python -m pip install --no-deps release/%OUT_WHEEL%
  EXIT /B %errorlevel%

:RunTests
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
  EXIT /B %RET_VALUE%

:Error
  EXIT /B 1

:End
  EXIT /B 0


