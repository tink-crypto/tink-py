workspace(name = "tink_py")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

load("@tink_py//:tink_py_deps.bzl", "tink_py_deps")

tink_py_deps()

load("@tink_py//:tink_py_deps_init.bzl", "tink_py_deps_init")

tink_py_deps_init("tink_py")

load("@tink_py_pip_deps//:requirements.bzl", tink_py_install_pypi_deps="install_deps")

tink_py_install_pypi_deps()
