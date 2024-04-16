workspace(name = "tink_py")

load("@tink_py//:tink_py_deps.bzl", "tink_py_deps", "tink_py_testonly_deps")

tink_py_deps()

load("@rules_python//python:repositories.bzl", "py_repositories")

py_repositories()

load("@tink_py//:tink_py_deps_init.bzl", "tink_py_deps_init")

tink_py_deps_init("tink_py")

tink_py_testonly_deps()

load("@tink_py_pip_deps//:requirements.bzl", tink_py_install_pypi_deps = "install_deps")

tink_py_install_pypi_deps()
