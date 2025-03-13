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

    maybe(
        http_archive,
        name = "com_google_protobuf",
        sha256 = "e9b9ac1910b1041065839850603caf36e29d3d3d230ddf52bd13778dd31b9046",
        strip_prefix = "protobuf-29.3",
        urls = ["https://github.com/protocolbuffers/protobuf/releases/download/v29.3/protobuf-29.3.zip"],
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

    maybe(
        http_archive,
        name = "com_google_absl",
        sha256 = "f50e5ac311a81382da7fa75b97310e4b9006474f9560ac46f54a9967f07d4ae3",
        strip_prefix = "abseil-cpp-20240722.0",
        urls = [
            "https://github.com/abseil/abseil-cpp/releases/download/20240722.0/abseil-cpp-20240722.0.tar.gz",
        ],
    )

    # Release from 2024-11-20.
    maybe(
        http_archive,
        name = "tink_cc",
        sha256 = "363ce671ab5ce0b24f279d3647185597a25f407c3608db007315f79f151f436b",
        strip_prefix = "tink-cc-2.3.0",
        urls = ["https://github.com/tink-crypto/tink-cc/releases/download/v2.3.0/tink-cc-2.3.0.zip"],
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
