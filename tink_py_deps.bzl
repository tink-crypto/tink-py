"""tink-py dependencies."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("@bazel_tools//tools/build_defs/repo:utils.bzl", "maybe")

def tink_py_deps():
    """Loads dependencies of tink-py."""

    maybe(
        http_archive,
        name = "bazel_skylib",
        sha256 = "bc283cdfcd526a52c3201279cda4bc298652efa898b10b4db0837dc51652756f",
        urls = [
            "https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/1.7.1/bazel-skylib-1.7.1.tar.gz",
            "https://github.com/bazelbuild/bazel-skylib/releases/download/1.7.1/bazel-skylib-1.7.1.tar.gz",
        ],
    )

    # Needed by com_google_protobuf.
    maybe(
        http_archive,
        name = "rules_java",
        urls = [
            "https://github.com/bazelbuild/rules_java/releases/download/7.12.5/rules_java-7.12.5.tar.gz",
        ],
        sha256 = "17b18cb4f92ab7b94aa343ce78531b73960b1bed2ba166e5b02c9fdf0b0ac270",
    )

    maybe(
        http_archive,
        name = "com_google_protobuf",
        sha256 = "6544e5ceec7f29d00397193360435ca8b3c4e843de3cf5698a99d36b72d65342",
        strip_prefix = "protobuf-30.2",
        urls = ["https://github.com/protocolbuffers/protobuf/releases/download/v30.2/protobuf-30.2.zip"],
        # Make sure we protobuf uses the same Abseil version as tink-cc@2.3.0.
        # This can be removed once tink-cc moves to
        # https://github.com/abseil/abseil-cpp/releases/tag/20250127.1.
        repo_mapping = {
            "@abseil-cpp": "@com_google_absl",
        },
    )

    maybe(
        http_archive,
        name = "rules_python",
        sha256 = "4f7e2aa1eb9aa722d96498f5ef514f426c1f55161c3c9ae628c857a7128ceb07",
        strip_prefix = "rules_python-1.0.0",
        url = "https://github.com/bazelbuild/rules_python/releases/download/1.0.0/rules_python-1.0.0.tar.gz",
    )

    # Release from 2023-07-17
    maybe(
        http_archive,
        name = "pybind11",
        build_file = "@pybind11_bazel//:pybind11.BUILD",
        sha256 = "d475978da0cdc2d43b73f30910786759d593a9d8ee05b1b6846d1eb16c6d2e0c",
        strip_prefix = "pybind11-2.11.1",
        urls = ["https://github.com/pybind/pybind11/archive/v2.11.1.tar.gz"],
    )

    # Release from 2023-08-11
    maybe(
        http_archive,
        name = "pybind11_bazel",
        sha256 = "e8355ee56c2ff772334b4bfa22be17c709e5573f6d1d561c7176312156c27bd4",
        strip_prefix = "pybind11_bazel-2.11.1",
        url = "https://github.com/pybind/pybind11_bazel/archive/refs/tags/v2.11.1.tar.gz",
    )

    # Release from 2025-05-06.
    maybe(
        http_archive,
        name = "tink_cc",
        sha256 = "06c4d49b0b1357f0b8c3abc77a7d920130dc868e4597d432a9ce1cda4f65e382",
        strip_prefix = "tink-cc-2.4.0",
        urls = ["https://github.com/tink-crypto/tink-cc/releases/download/v2.4.0/tink-cc-2.4.0.zip"],
    )

def tink_py_testonly_deps():
    """Test only dependencies."""

    # Note: sha256 is intentionally omitted as this is not a static resource.
    # Whenever updated, clients should fetch the latest revision provided at
    # this URL.
    maybe(
        http_file,
        name = "google_root_pem",
        executable = 0,
        urls = ["https://pki.goog/roots.pem"],
    )

    # Release from 2023-08-02
    maybe(
        http_archive,
        name = "com_google_googletest",
        sha256 = "1f357c27ca988c3f7c6b4bf68a9395005ac6761f034046e9dde0896e3aba00e4",
        strip_prefix = "googletest-1.14.0",
        url = "https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip",
    )
