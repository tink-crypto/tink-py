# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Setup for the tink-py package with pip.

The behavior of this script can be modified using two enviroment variables:

  - TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION: To change the version that is used.
  - TINK_PYTHON_SETUPTOOLS_LOCAL_TINK_CC_PATH: Local tink-cc to use.
"""

import glob
import os
import platform
import posixpath
import re
import shutil
import subprocess
from typing import List

import setuptools
from setuptools.command import build_ext

_PROJECT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_TINK_CRYPTO_GITHUB_ORG_URL = 'https://github.com/tink-crypto'


def _get_tink_version() -> str:
  """Returns the project version.

  If the TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION environment variable is set,
  this function returns its value; otherwise, it parses the value in VERSION.
  """
  if 'TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION' in os.environ:
    return os.environ['TINK_PYTHON_SETUPTOOLS_OVERRIDE_VERSION']
  with open(os.path.join(_PROJECT_BASE_DIR, 'VERSION')) as f:
    version = f.read().strip()
    if not re.fullmatch(r'[0-9]+.[0-9]+.[0-9]+', version):
      raise ValueError(f'Invalid version: {version}')
    return version


def _get_bazel_command() -> str:
  """Finds the bazel command."""
  if shutil.which('bazelisk'):
    return 'bazelisk'
  elif shutil.which('bazel'):
    return 'bazel'
  raise FileNotFoundError(
      'Could not find bazel executable. Please install '
      'bazel to compile the Tink Python package.'
  )


def _get_protoc_command() -> str:
  """Finds the protoc command."""
  if 'PROTOC' in os.environ and os.path.exists(os.environ['PROTOC']):
    return os.environ['PROTOC']
  protoc_path = shutil.which('protoc')
  if protoc_path is None:
    raise FileNotFoundError(
        'Could not find protoc executable. Please install '
        'protoc to compile the Tink Python package.'
    )
  return protoc_path


def _generate_proto(protoc: str, source: str) -> None:
  """Invokes protoc to generate a _pb2.py from .proto files."""
  if not os.path.exists(source):
    raise FileNotFoundError(f'Cannot find required file: {source}')

  output = source.replace('.proto', '_pb2.py')

  if os.path.exists(output) and os.path.getmtime(source) < os.path.getmtime(
      output
  ):
    # No need to regenerate if output is newer than source.
    return

  print(f'Generating {output}...')
  protoc_args = [protoc, '-I.', '--python_out=.', source]
  subprocess.run(args=protoc_args, check=True)


def _parse_requirements(requirements_filename: str) -> List[str]:
  """Parses requirements from the given file."""
  with open(os.path.join(_PROJECT_BASE_DIR, requirements_filename)) as f:
    return [
        line.rstrip()
        for line in f
        if not (line.isspace() or line.startswith('#'))
    ]


class BazelExtension(setuptools.Extension):
  """A C/C++ extension that is defined as a Bazel BUILD target."""

  def __init__(self, bazel_target: str, target_name: str = '') -> None:
    self.bazel_target = bazel_target
    self.relpath, self.target_name = posixpath.relpath(
        bazel_target, '//'
    ).split(':')
    if target_name:
      self.target_name = target_name
    ext_name = os.path.join(
        self.relpath.replace(posixpath.sep, os.path.sep), self.target_name
    )
    setuptools.Extension.__init__(self, ext_name, sources=[])


class BuildBazelExtension(build_ext.build_ext):
  """A command that runs Bazel to build a C/C++ extension."""

  def __init__(self, dist: str) -> None:
    super().__init__(dist)
    self.bazel_command = _get_bazel_command()

  def run(self) -> None:
    for ext in self.extensions:
      self.bazel_build(ext)
    build_ext.build_ext.run(self)

  def bazel_build(self, ext: str) -> None:
    if not os.path.exists(self.build_temp):
      os.makedirs(self.build_temp)

    # Ensure no artifacts from previous builds are reused (i.e. from builds
    # using a different Python version).
    bazel_clean_argv = [self.bazel_command, 'clean', '--expunge']
    self.spawn(bazel_clean_argv)

    bazel_argv = [
        self.bazel_command,
        'build',
        ext.bazel_target,
        '--compilation_mode=' + ('dbg' if self.debug else 'opt'),
    ]

    if platform.system() == 'Darwin':
      # Set the minimum macOS version to support based on
      # MACOSX_DEPLOYMENT_TARGET. This mimics the CMake behavior: when
      # MACOSX_DEPLOYMENT_TARGET is set, use its value to determine the minimum
      # OS version.
      #
      # See https://github.com/bazelbuild/bazel/issues/16932.
      # NOTE: If macos_minimum_os is unspecified, Bazel uses the default value
      # of macos_sdk_version which is taken from the default system Xcode:
      # https://bazel.build/reference/command-line-reference#flag--macos_minimum_os.
      deployment_target = os.getenv('MACOSX_DEPLOYMENT_TARGET', '')
      if deployment_target:
        bazel_argv += [f'--macos_minimum_os={deployment_target}']

      archflags = os.getenv('ARCHFLAGS', '')
      if platform.machine() == 'x86_64' and 'arm64' in archflags:
        # We are cross compiling for arm64; set the correct CPU params.
        bazel_argv += ['--cpu=darwin_arm64', '--macos_cpus=arm64']

    self.spawn(bazel_argv)
    ext_bazel_bin_path = os.path.join(
        'bazel-bin', ext.relpath, ext.target_name + '.so'
    )
    ext_dest_path = self.get_ext_fullpath(ext.name)
    ext_dest_dir = os.path.dirname(ext_dest_path)
    if not os.path.exists(ext_dest_dir):
      os.makedirs(ext_dest_dir)
    shutil.copyfile(ext_bazel_bin_path, ext_dest_path)


def main() -> None:
  # Generate compiled protocol buffers.
  protoc_command = _get_protoc_command()
  for proto_file in glob.glob('tink/proto/*.proto'):
    _generate_proto(protoc_command, proto_file)

  gcpkms_extra_requirements = _parse_requirements('requirements_gcpkms.in')
  awskms_extra_requirements = _parse_requirements('requirements_awskms.in')

  setuptools.setup(
      name='tink',
      version=_get_tink_version(),
      url=f'{_TINK_CRYPTO_GITHUB_ORG_URL}/tink-py',
      description=(
          'A multi-language, cross-platform library that provides cryptographic'
          ' APIs that are secure, easy to use correctly, and hard(er) to'
          ' misuse.'
      ),
      author='Tink Developers',
      author_email='tink-users@googlegroups.com',
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      # Contained modules and scripts.
      packages=setuptools.find_packages(),
      install_requires=_parse_requirements('requirements.in'),
      extras_require={
          'gcpkms': gcpkms_extra_requirements,
          'awskms': awskms_extra_requirements,
          'all': gcpkms_extra_requirements + awskms_extra_requirements,
      },
      cmdclass=dict(build_ext=BuildBazelExtension),
      ext_modules=[
          BazelExtension('//tink/cc/pybind:tink_bindings'),
      ],
      zip_safe=False,
      # PyPI package information.
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Topic :: Software Development :: Libraries',
      ],
      license='Apache 2.0',
      keywords='tink cryptography',
      python_requires='>=3.8',
  )


if __name__ == '__main__':
  main()
