"""tink-py dependencies."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")

def tink_py_deps():
    """Loads dependencies of tink-py."""
    if not native.existing_rule("google_root_pem"):
        http_file(
            name = "google_root_pem",
            executable = 0,
            sha256 = "1acf0d4780541758be2c0f998e1e0275232626ed3f8793d8e2fe8e2753750613",
            urls = ["https://pki.goog/roots.pem"],
        )

    if not native.existing_rule("bazel_skylib"):
        http_archive(
            name = "bazel_skylib",
            sha256 = "cd55a062e763b9349921f0f5db8c3933288dc8ba4f76dd9416aac68acee3cb94",
            urls = [
                "https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/1.5.0/bazel-skylib-1.5.0.tar.gz",
                "https://github.com/bazelbuild/bazel-skylib/releases/download/1.5.0/bazel-skylib-1.5.0.tar.gz",
            ],
        )

    if not native.existing_rule("com_google_protobuf"):
        # Release X.25.1 from 2023-11-15.
        http_archive(
            name = "com_google_protobuf",
            sha256 = "5c86c077b0794c3e9bb30cac872cf883043febfb0f992137f0a8b1c3d534617c",
            strip_prefix = "protobuf-25.1",
            urls = ["https://github.com/protocolbuffers/protobuf/releases/download/v25.1/protobuf-25.1.zip"],
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
            urls = ["https://github.com/tink-crypto/tink-cc/releases/download/v2.1.0/tink-cc-2.1.0.zip"],
            strip_prefix = "tink-cc-2.1.0",
            sha256 = "3804afecbe7096d3786b660e9cd5f365f064743eec52d76984abb9da38dd0fb3",
        )
