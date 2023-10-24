"""Initialization of tink-py dependencies."""

load("@pybind11_bazel//:python_configure.bzl", "python_configure")
load("@rules_python//python:pip.bzl", "pip_parse")
load("@tink_cc//:tink_cc_deps.bzl", "tink_cc_deps")
load("@tink_cc//:tink_cc_deps_init.bzl", "tink_cc_deps_init")

def tink_py_deps_init(workspace_name):
    tink_cc_deps()

    tink_cc_deps_init()

    pip_parse(
        name = "tink_py_pip_deps",
        extra_pip_args = ["--no-deps"],
        quiet = False,
        requirements_lock = "@" + workspace_name + "//:requirements_all.txt",
    )

    # Use `which python3` by default [1] unless PYTHON_BIN_PATH is specified [2].
    #
    # [1] https://github.com/pybind/pybind11_bazel/blob/fc56ce8a8b51e3dd941139d329b63ccfea1d304b/python_configure.bzl#L434
    # [2] https://github.com/pybind/pybind11_bazel/blob/fc56ce8a8b51e3dd941139d329b63ccfea1d304b/python_configure.bzl#L162
    python_configure(name = "local_config_python", python_version = "3")
