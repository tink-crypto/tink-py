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
"""Setup for the tink-py package with pip."""
from distutils import spawn

import glob
import os
import posixpath
import shutil
import subprocess
import textwrap

from typing import List

import setuptools
from setuptools.command import build_ext

_PROJECT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_TINK_CRYPTO_GITHUB_ORG_URL = 'https://github.com/tink-crypto'


def _get_tink_version() -> str:
  """Parses the version number from VERSION file."""
  with open(os.path.join(_PROJECT_BASE_DIR, 'VERSION')) as f:
    try:
      version_line = next(
          line for line in f if line.startswith('TINK_VERSION_LABEL'))
    except StopIteration:
      raise ValueError(
          f'Version not defined in {_PROJECT_BASE_DIR}/VERSION') from None
    else:
      return version_line.split(' = ')[-1].strip('\n \'"')


def _get_bazel_command() -> str:
  """Finds the bazel command."""
  if spawn.find_executable('bazelisk'):
    return 'bazelisk'
  elif spawn.find_executable('bazel'):
    return 'bazel'
  raise FileNotFoundError('Could not find bazel executable. Please install '
                          'bazel to compile the Tink Python package.')


def _get_protoc_command() -> str:
  """Finds the protoc command."""
  if 'PROTOC' in os.environ and os.path.exists(os.environ['PROTOC']):
    return os.environ['PROTOC']
  else:
    return spawn.find_executable('protoc')
  raise FileNotFoundError('Could not find protoc executable. Please install '
                          'protoc to compile the Tink Python package.')


def _generate_proto(protoc: str, source: str) -> None:
  """Invokes protoc to generate a _pb2.py from .proto files."""
  if not os.path.exists(source):
    raise FileNotFoundError(f'Cannot find required file: {source}')

  output = source.replace('.proto', '_pb2.py')

  if (os.path.exists(output) and
      os.path.getmtime(source) < os.path.getmtime(output)):
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


def _patch_workspace(workspace_content: str) -> str:
  """Update the Bazel workspace with valid repository references.

  setuptools builds in a temporary folder which breaks the relative paths
  defined in the Bazel workspace. By default, the WORKSPACE file contains
  http_archive rules that contain URLs pointing to archives of the tink-cc,
  tink-cc-awskms and tink-cc-gcpkm GitHub repositories
  at the latest commit on their main branch.

  This behavior can be modified via the following environment variables, in
  order of precedence:

    * TINK_PYTHON_SETUPTOOLS_OVERRIDE_BASE_PATH
        Instead of using http_archive() rules, update the local_repository()
        rules for tink-cc, tink-cc-awskms and tink-cc-gcpkms located at the
        given base path, that is:
          ${TINK_PYTHON_SETUPTOOLS_OVERRIDE_BASE_PATH}/tink_cc
          ${TINK_PYTHON_SETUPTOOLS_OVERRIDE_BASE_PATH}/tink_cc_awskms
          ${TINK_PYTHON_SETUPTOOLS_OVERRIDE_BASE_PATH}/tink_cc_gcpkms

    * TINK_PYTHON_SETUPTOOLS_OVERRIDE_TAGGED_VERSIONS
        Instead of fetching dependencies from the main branch fetch
        archives that correspond with the given tagged versions of tink-cc,
        tink-cc-awskms and tink-cc-gcpkms specified as a list of comma separated
        values, e.g., "main,1.8.2,2.0.1" means
        tink-cc@main, tink-cc-awskms@1.8.2, tink-cc-gcpkms@2.0.1.

  Args:
    workspace_content: The original WORKSPACE.

  Returns:
    The patched workspace_content with either local or remote dependencies.
  """

  if 'TINK_PYTHON_SETUPTOOLS_OVERRIDE_BASE_PATH' in os.environ:
    base_path = os.environ['TINK_PYTHON_SETUPTOOLS_OVERRIDE_BASE_PATH']
    return _patch_http_archive_with_local_repo(workspace_content, base_path)

  if 'TINK_PYTHON_SETUPTOOLS_OVERRIDE_TAGGED_VERSIONS' in os.environ:
    tagged_versions = os.environ[
        'TINK_PYTHON_SETUPTOOLS_OVERRIDE_TAGGED_VERSIONS'].split(',')
    return _patch_http_archive_with_tagged_version(workspace_content,
                                                   tagged_versions)
  # Nothing to do, dependencies are fetched from main.
  return workspace_content


def _patch_http_archive_with_tagged_version(workspace_content: str,
                                            tagged_versions: List[str]) -> str:
  """Replaces the archive from main to versioned."""
  if len(tagged_versions) != 3:
    raise ValueError(
        f'Invalid tagged versions for Tink C++ dependencies: {tagged_versions}')

  workspace_content = workspace_content.replace(
      'tink-cc/archive/main.zip',
      f'tink-cc/archive/v{tagged_versions[0]}.zip')
  workspace_content = workspace_content.replace(
      'strip_prefix = "tink-cc-main"',
      f'strip_prefix = "tink-cc-{tagged_versions[0]}"')

  workspace_content = workspace_content.replace(
      'tink-cc-awskms/archive/main.zip',
      f'tink-cc-awskms/archive/v{tagged_versions[1]}.zip')
  workspace_content = workspace_content.replace(
      'strip_prefix = "tink-cc-awskms-main"',
      f'strip_prefix = "tink-cc-awskms-{tagged_versions[1]}"')

  workspace_content = workspace_content.replace(
      'tink-cc-gcpkms/archive/main.zip',
      f'tink-cc-gcpkms/archive/v{tagged_versions[2]}.zip')
  workspace_content = workspace_content.replace(
      'strip_prefix = "tink-cc-gcpkms-main"',
      f'strip_prefix = "tink-cc-gcpkms-{tagged_versions[2]}"')

  return workspace_content


def _replace_http_archive_with_local_repo(workspace_content: str, name: str,
                                          repo_name: str, local_path: str,
                                          archive_filename: str,
                                          strip_prefix: str) -> str:
  """Replaces http_archive rule with local_repository in workspace_content."""
  before = textwrap.dedent(f"""\
      http_archive(
          name = "{name}",
          urls = ["{_TINK_CRYPTO_GITHUB_ORG_URL}/{repo_name}/archive/{archive_filename}"],
          strip_prefix = "{strip_prefix}",
      )
      """)
  after = textwrap.dedent(f"""\
      # Modified by setup.py
      local_repository(
          name = "{name}",
          path = "{local_path}",
      )
      """)
  return workspace_content.replace(before, after)


def _patch_http_archive_with_local_repo(workspace_content: str,
                                        base_path: str) -> str:
  """Patches workspace_content replacing http_archive rules with local_repository."""
  workspace_content = workspace_content.replace(
      'load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")\n',
      '')

  workspace_content = _replace_http_archive_with_local_repo(
      workspace_content=workspace_content,
      name='tink_cc',
      repo_name='tink-cc',
      local_path=f'{base_path}/tink_cc',
      archive_filename='main.zip',
      strip_prefix='tink-cc-main')

  workspace_content = _replace_http_archive_with_local_repo(
      workspace_content=workspace_content,
      name='tink_cc_awskms',
      repo_name='tink-cc-awskms',
      local_path=f'{base_path}/tink_cc_awskms',
      archive_filename='main.zip',
      strip_prefix='tink-cc-awskms-main')

  workspace_content = _replace_http_archive_with_local_repo(
      workspace_content=workspace_content,
      name='tink_cc_gcpkms',
      repo_name='tink-cc-gcpkms',
      local_path=f'{base_path}/tink_cc_gcpkms',
      archive_filename='main.zip',
      strip_prefix='tink-cc-gcpkms-main')

  return workspace_content


class BazelExtension(setuptools.Extension):
  """A C/C++ extension that is defined as a Bazel BUILD target."""

  def __init__(self, bazel_target: str, target_name: str = '') -> None:
    self.bazel_target = bazel_target
    self.relpath, self.target_name = (
        posixpath.relpath(bazel_target, '//').split(':'))
    if target_name:
      self.target_name = target_name
    ext_name = os.path.join(
        self.relpath.replace(posixpath.sep, os.path.sep), self.target_name)
    setuptools.Extension.__init__(self, ext_name, sources=[])


class BuildBazelExtension(build_ext.build_ext):
  """A command that runs Bazel to build a C/C++ extension."""

  def __init__(self, dist: str) -> None:
    super(BuildBazelExtension, self).__init__(dist)
    self.bazel_command = _get_bazel_command()

  def run(self) -> None:
    for ext in self.extensions:
      self.bazel_build(ext)
    build_ext.build_ext.run(self)

  def bazel_build(self, ext: str) -> None:
    # Change WORKSPACE to include tink_cc from an archive
    with open('WORKSPACE', 'r') as f:
      workspace_contents = f.read()
    with open('WORKSPACE', 'w') as f:
      f.write(_patch_workspace(workspace_contents))

    if not os.path.exists(self.build_temp):
      os.makedirs(self.build_temp)

    # Ensure no artifacts from previous builds are reused (i.e. from builds
    # using a different Python version).
    bazel_clean_argv = [self.bazel_command, 'clean', '--expunge']
    self.spawn(bazel_clean_argv)

    bazel_argv = [
        self.bazel_command, 'build', ext.bazel_target,
        '--compilation_mode=' + ('dbg' if self.debug else 'opt'),
        '--incompatible_linkopts_to_linklibs'
        # TODO(https://github.com/bazelbuild/bazel/issues/9254): Remove linkopts
        # flag when issue is fixed.
    ]
    self.spawn(bazel_argv)
    ext_bazel_bin_path = os.path.join('bazel-bin', ext.relpath,
                                      ext.target_name + '.so')
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

  setuptools.setup(
      name='tink',
      version=_get_tink_version(),
      url=f'{_TINK_CRYPTO_GITHUB_ORG_URL}/tink-py',
      description='A multi-language, cross-platform library that provides '
      'cryptographic APIs that are secure, easy to use correctly, and hard(er) '
      'to misuse.',
      author='Tink Developers',
      author_email='tink-users@googlegroups.com',
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      # Contained modules and scripts.
      packages=setuptools.find_packages(),
      install_requires=_parse_requirements('requirements.in'),
      cmdclass=dict(build_ext=BuildBazelExtension),
      ext_modules=[
          BazelExtension('//tink/cc/pybind:tink_bindings'),
      ],
      zip_safe=False,
      # PyPI package information.
      classifiers=[
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Topic :: Software Development :: Libraries',
      ],
      license='Apache 2.0',
      keywords='tink cryptography',
  )


if __name__ == '__main__':
  main()
