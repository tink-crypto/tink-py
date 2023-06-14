"""tink-py dependencies."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")

def tink_py_deps():
    """Loads dependencies of tink-py."""
    if not native.existing_rule("google_root_pem"):
        http_file(
            name = "google_root_pem",
            executable = 0,
            urls = ["https://pki.goog/roots.pem"],
            sha256 = "9c9b9685ad319b9747c3fe69b46a61c11a0efabdfa09ca6a8b0c3da421036d27",
        )

    if not native.existing_rule("rules_python"):
        # Release from 2022-07-15
        http_archive(
            name = "rules_python",
            sha256 = "a3a6e99f497be089f81ec082882e40246bfd435f52f4e82f37e89449b04573f6",
            strip_prefix = "rules_python-0.10.2",
            url = "https://github.com/bazelbuild/rules_python/archive/refs/tags/0.10.2.tar.gz",
        )

    if not native.existing_rule("pybind11"):
        # Commit from 2021-12-28
        http_archive(
            name = "pybind11",
            build_file = "@pybind11_bazel//:pybind11.BUILD",
            strip_prefix = "pybind11-2.9.0",
            urls = ["https://github.com/pybind/pybind11/archive/v2.9.0.tar.gz"],
            sha256 = "057fb68dafd972bc13afb855f3b0d8cf0fa1a78ef053e815d9af79be7ff567cb",
        )

    if not native.existing_rule("pybind11_bazel"):
        # Commit from 2023-05-03
        http_archive(
            name = "pybind11_bazel",
            strip_prefix = "pybind11_bazel-b162c7c88a253e3f6b673df0c621aca27596ce6b",
            url = "https://github.com/pybind/pybind11_bazel/archive/b162c7c88a253e3f6b673df0c621aca27596ce6b.zip",
            sha256 = "b72c5b44135b90d1ffaba51e08240be0b91707ac60bea08bb4d84b47316211bb",
        )
