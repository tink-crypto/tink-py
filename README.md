# Tink Python

<!-- GCP Ubuntu --->

[tink_py_bazel_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-bazel-gcp-ubuntu.svg
[tink_py_bazel_kms_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-bazel-kms-gcp-ubuntu.svg
[tink_py_pip_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-pip-gcp-ubuntu.svg
[tink_py_pip_kms_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-pip-kms-gcp-ubuntu.svg
[tink_py_bdist_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-release-bdist-create-gcp-ubuntu.svg
[tink_py_sdist_create_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-release-sdist-create-gcp-ubuntu.svg
[tink_py_sdist_test_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-release-sdist-test-gcp-ubuntu.svg

<!-- GCP Ubuntu (aarch64) --->

[tink_py_bdist_create_badge_gcp_ubuntu_aarch64]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-release-bdist-create-gcp_ubuntu-arm64-external.svg

<!-- MacOS --->

[tink_py_bazel_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-bazel-macos-external.svg
[tink_py_bazel_kms_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-bazel-kms-macos-external.svg
[tink_py_pip_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-pip-macos-external.svg
[tink_py_pip_kms_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-pip-kms-macos-external.svg
[tink_py_bdist_create_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-release-bdist-create-macos-external.svg

**Test**              | **GCP Ubuntu**                                                        | **GCP Ubuntu (aarch64)**                                                       | **MacOS**
--------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------
Bazel                 | [![Bazel_GcpUbuntu][tink_py_bazel_badge_gcp_ubuntu]](#)               | N/A                                                                            | [![Bazel_MacOs][tink_py_bazel_badge_macos]](#)
Bazel (with KMS)      | [![Bazel_Kms_GcpUbuntu][tink_py_bazel_kms_badge_gcp_ubuntu]](#)       | N/A                                                                            | [![Bazel_Kms_MacOs][tink_py_bazel_kms_badge_macos]](#)
Pip                   | [![Pip_MacOs][tink_py_pip_badge_gcp_ubuntu]](#)                       | N/A                                                                            | [![Pip_MacOs][tink_py_pip_badge_macos]](#)
Pip (with KMS)        | [![Pip_Kms_GcpUbuntu][tink_py_pip_kms_badge_gcp_ubuntu]](#)           | N/A                                                                            | [![Pip_Kms_MacOs][tink_py_pip_kms_badge_macos]](#)
Bdist (Create + Test) | [![Bdist_GcpUbuntu][tink_py_bdist_badge_gcp_ubuntu]](#)               | [![Bdist_GcpUbuntu_Aarch64][tink_py_bdist_create_badge_gcp_ubuntu_aarch64]](#) | [![Bdist_MacOs][tink_py_bdist_create_badge_macos]](#)
Sdist (Create)        | [![Sdist_Create_GcpUbuntu][tink_py_sdist_create_badge_gcp_ubuntu]](#) | N/A                                                                            | N/A
Sdist (Test)          | [![Sdist_Test_GcpUbuntu][tink_py_sdist_test_badge_gcp_ubuntu]](#)     | N/A                                                                            | N/A


Using crypto in your application [shouldn't have to][devs_are_users_too_slides]
feel like juggling chainsaws in the dark. Tink is a crypto library written by a
group of cryptographers and security engineers at Google. It was born out of our
extensive experience working with Google's product teams,
[fixing weaknesses in implementations](https://github.com/google/wycheproof),
and providing simple APIs that can be used safely without needing a crypto
background.

Tink provides secure APIs that are easy to use correctly and hard(er) to misuse.
It reduces common crypto pitfalls with user-centered design, careful
implementation and code reviews, and extensive testing. At Google, Tink is one
of the standard crypto libraries, and has been deployed in hundreds of products
and systems.

To get a quick overview of Tink's design please take a look at
[Tink's goals](https://developers.google.com/tink/design/goals_of_tink).

The official documentation is available at https://developers.google.com/tink.

[devs_are_users_too_slides]: https://www.usenix.org/sites/default/files/conference/protected-files/hotsec15_slides_green.pdf

## Contact and mailing list

If you want to contribute, please read [CONTRIBUTING](docs/CONTRIBUTING.md) and
send us pull requests. You can also report bugs or file feature requests.

If you'd like to talk to the developers or get notified about major product
updates, you may want to subscribe to our
[mailing list](https://groups.google.com/forum/#!forum/tink-users).

## Maintainers

Tink is maintained by (A-Z):

-   Moreno Ambrosin
-   Taymon Beal
-   William Conner
-   Thomas Holenstein
-   Stefan Kölbl
-   Charles Lee
-   Cindy Lin
-   Fernando Lobato Meeser
-   Ioana Nedelcu
-   Sophie Schmieg
-   Elizaveta Tretiakova
-   Jürg Wullschleger

Alumni:

-   Haris Andrianakis
-   Daniel Bleichenbacher
-   Tanuj Dhir
-   Thai Duong
-   Atul Luykx
-   Rafael Misoczki
-   Quan Nguyen
-   Bartosz Przydatek
-   Enzo Puig
-   Laurent Simon
-   Veronika Slívová
-   Paula Vidas
