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
set OLD_PATH=%PATH%

set /p TINK_VERSION=<VERSION
ECHO %%KOKORO_JOB_NAME%% | FINDSTR "release"
IF errorlevel 1 (
  set TINK_VERSION=%TINK_VERSION%.dev0
)
set TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION=%TINK_VERSION%

call :UsePython "3.8.10" "38"
call :BuildAndInstallWheel
call :RunTests
@REM Build wheels for 3.9 and 3.10 only on release jobs.
ECHO %%KOKORO_JOB_NAME%% | FINDSTR "release"
IF errorlevel 0 (
  call :UsePython "3.9.13" "39"
  call :BuildAndInstallWheel
  call :RunTests
  call :UsePython "3.10.11" "310"
  call :BuildAndInstallWheel
  call :RunTests
)
call :UsePython "3.11.7" "311"
call :BuildAndInstallWheel
call :RunTests

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
  set PATH=C:\Python%~2\;C:\Python%~2\Scripts;%OLD_PATH%
  python -m pip install --no-deps --require-hashes -r ^
    tools\distribution\requirements.txt
  python -m pip install --upgrade delvewheel
  set OUT_WHEEL=tink-%TINK_VERSION%-cp%~2-cp%~2-win_amd64.whl
  EXIT /B 0

:BuildAndInstallWheel
  python -m pip wheel .
  @REM Repair the wheel and place it in release/.
  python -m delvewheel repair %OUT_WHEEL% -w release
  python -m pip install release/%OUT_WHEEL%
  EXIT /B 0

:RunTests
  FOR /F %%x in ('DIR /s/b tink\*_test.py') DO (
  ECHO %%x | FINDSTR "integration pybind" 1>nul
    IF errorlevel 1 (
      python %%x
    ) ELSE (
      ECHO "Skip test file %%x"
    )
  )
  EXIT /B 0

:End
EXIT /B 0


