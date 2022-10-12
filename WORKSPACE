workspace(name = "tink_py")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# All the dependencies below are at HEAD.
http_archive(
    name = "tink_cc",
    urls = ["https://github.com/tink-crypto/tink-cc/archive/main.zip"],
    strip_prefix = "tink-cc-main",
)

http_archive(
    name = "tink_cc_awskms",
    urls = ["https://github.com/tink-crypto/tink-cc-awskms/archive/main.zip"],
    strip_prefix = "tink-cc-awskms-main",
)

http_archive(
    name = "tink_cc_gcpkms",
    urls = ["https://github.com/tink-crypto/tink-cc-gcpkms/archive/main.zip"],
    strip_prefix = "tink-cc-gcpkms-main",
)

# Need to load rules_python earlier as proto uses an older version which is
# incompatible with our Python implementation will load
load("@tink_py//:tink_py_deps.bzl", "tink_py_deps")

tink_py_deps()

load("@tink_py//:tink_py_deps_init.bzl", "tink_py_deps_init")

tink_py_deps_init("tink_py")

load("@tink_cc//:tink_cc_deps.bzl", "tink_cc_deps")

tink_cc_deps()

load("@tink_cc//:tink_cc_deps_init.bzl", "tink_cc_deps_init")

tink_cc_deps_init()

load("@tink_cc_awskms//:tink_cc_awskms_deps.bzl", "tink_cc_awskms_deps")

tink_cc_awskms_deps()

load("@tink_cc_gcpkms//:tink_cc_gcpkms_deps.bzl", "tink_cc_gcpkms_deps")

tink_cc_gcpkms_deps()

load("@tink_cc_gcpkms//:tink_cc_gcpkms_deps_init.bzl", "tink_cc_gcpkms_deps_init")

tink_cc_gcpkms_deps_init()
