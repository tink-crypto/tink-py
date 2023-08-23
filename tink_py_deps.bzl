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

    if not native.existing_rule("bazel_skylib"):
        http_archive(
            name = "bazel_skylib",
            sha256 = "66ffd9315665bfaafc96b52278f57c7e2dd09f5ede279ea6d39b2be471e7e3aa",
            urls = [
                "https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/1.4.2/bazel-skylib-1.4.2.tar.gz",
                "https://github.com/bazelbuild/bazel-skylib/releases/download/1.4.2/bazel-skylib-1.4.2.tar.gz",
            ],
        )

    if not native.existing_rule("com_google_protobuf"):
        # Release X.21.9 from 2022-10-26.
        http_archive(
            name = "com_google_protobuf",
            strip_prefix = "protobuf-21.9",
            urls = ["https://github.com/protocolbuffers/protobuf/archive/refs/tags/v21.9.zip"],
            sha256 = "5babb8571f1cceafe0c18e13ddb3be556e87e12ceea3463d6b0d0064e6cc1ac3",
        )

    if not native.existing_rule("rules_python"):
        # Release from 2023-07-12
        http_archive(
            name = "rules_python",
            sha256 = "0a8003b044294d7840ac7d9d73eef05d6ceb682d7516781a4ec62eeb34702578",
            strip_prefix = "rules_python-0.24.0",
            url = "https://github.com/bazelbuild/rules_python/releases/download/0.24.0/rules_python-0.24.0.tar.gz",
        )

    if not native.existing_rule("pybind11"):
        # Release from 2023-07-17
        http_archive(
            name = "pybind11",
            build_file = "@pybind11_bazel//:pybind11.BUILD",
            strip_prefix = "pybind11-2.11.1",
            urls = ["https://github.com/pybind/pybind11/archive/v2.11.1.tar.gz"],
            sha256 = "d475978da0cdc2d43b73f30910786759d593a9d8ee05b1b6846d1eb16c6d2e0c",
        )

    if not native.existing_rule("pybind11_bazel"):
        # Release from 2023-08-11
        http_archive(
            name = "pybind11_bazel",
            strip_prefix = "pybind11_bazel-2.11.1",
            url = "https://github.com/pybind/pybind11_bazel/archive/refs/tags/v2.11.1.tar.gz",
            sha256 = "e8355ee56c2ff772334b4bfa22be17c709e5573f6d1d561c7176312156c27bd4",
        )

    if not native.existing_rule("tink_cc"):
        http_archive(
            name = "tink_cc",
            urls = ["https://github.com/tink-crypto/tink-cc/archive/refs/tags/v2.0.0.zip"],
            strip_prefix = "tink-cc-2.0.0",
            sha256 = "103ddfce800e77f3b3b6b2c808a8611bc734b31ddb12fbcfd8bebc1b96a7e963",
        )
