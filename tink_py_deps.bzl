"""tink-py dependencies."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("@bazel_tools//tools/build_defs/repo:utils.bzl", "maybe")

def tink_py_deps():
    """Loads dependencies of tink-py."""

    maybe(
        http_archive,
        name = "bazel_skylib",
        sha256 = "cd55a062e763b9349921f0f5db8c3933288dc8ba4f76dd9416aac68acee3cb94",
        urls = [
            "https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/1.5.0/bazel-skylib-1.5.0.tar.gz",
            "https://github.com/bazelbuild/bazel-skylib/releases/download/1.5.0/bazel-skylib-1.5.0.tar.gz",
        ],
    )

    # Release from 2023-11-15
    maybe(
        http_archive,
        name = "com_google_protobuf",
        sha256 = "5c86c077b0794c3e9bb30cac872cf883043febfb0f992137f0a8b1c3d534617c",
        strip_prefix = "protobuf-25.1",
        urls = ["https://github.com/protocolbuffers/protobuf/releases/download/v25.1/protobuf-25.1.zip"],
    )

    # Release from 2024-02-13
    maybe(
        http_archive,
        name = "rules_python",
        sha256 = "c68bdc4fbec25de5b5493b8819cfc877c4ea299c0dcb15c244c5a00208cde311",
        strip_prefix = "rules_python-0.31.0",
        url = "https://github.com/bazelbuild/rules_python/releases/download/0.31.0/rules_python-0.31.0.tar.gz",
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

    # Release from 2023-09-18
    maybe(
        http_archive,
        name = "com_google_absl",
        sha256 = "497ebdc3a4885d9209b9bd416e8c3f71e7a1fb8af249f6c2a80b7cbeefcd7e21",
        strip_prefix = "abseil-cpp-20230802.1",
        urls = ["https://github.com/abseil/abseil-cpp/archive/refs/tags/20230802.1.zip"],
    )

    # Release from 2024-04-23
    maybe(
        http_archive,
        name = "tink_cc",
        sha256 = "14a3f64a56d7e9296889d7eba7a3b8787c3281e5bc5791033c54baf810a0b6ef",
        strip_prefix = "tink-cc-2.1.3",
        urls = ["https://github.com/tink-crypto/tink-cc/releases/download/v2.1.3/tink-cc-2.1.3.zip"],
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
