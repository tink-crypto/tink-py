# Tink Python

<!-- GCP Ubuntu --->

[tink_py_bazel_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-bazel-gcp-ubuntu.svg
[tink_py_examples_bazel_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-examples-bazel-gcp-ubuntu.svg
[tink_py_examples_bazel_kms_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-examples-bazel-kms-gcp-ubuntu.svg
[tink_py_pip_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-pip-gcp-ubuntu.svg
[tink_py_release_badge_gcp_ubuntu]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-release-gcp-ubuntu.svg

<!-- MacOS --->

[tink_py_bazel_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-bazel-macos-external.svg
[tink_py_examples_bazel_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-examples-bazel-macos-external.svg
[tink_py_examples_bazel_kms_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-examples-bazel-kms-macos-external.svg
[tink_py_pip_badge_macos]: https://storage.googleapis.com/tink-kokoro-build-badges/tink-py-pip-macos-external.svg

**Test**               | **GCP Ubuntu**                                                                    | **MacOS**
---------------------- | --------------------------------------------------------------------------------- | ---------
Tink (Bazel)           | [![Bazel_GcpUbuntu][tink_py_bazel_badge_gcp_ubuntu]](#)                           | [![Bazel_MacOs][tink_py_bazel_badge_macos]](#)
Tink Examples          | [![Examples_Bazel_GcpUbuntu][tink_py_examples_bazel_badge_gcp_ubuntu]](#)         | [![Examples_Bazel_MacOs][tink_py_examples_bazel_badge_macos]](#)
Tink Examples with KMS | [![Examples_Bazel_Kms_GcpUbuntu][tink_py_examples_bazel_kms_badge_gcp_ubuntu]](#) | [![Examples_Bazel_Kms_MacOs][tink_py_examples_bazel_kms_badge_macos]](#)
Tink Pip               | [![Pip_MacOs][tink_py_pip_badge_gcp_ubuntu]](#)                                   | [![Pip_GcpUbuntu][tink_py_pip_badge_macos]](#)
Tink Release           | [![Release_GcpUbuntu][tink_py_release_badge_gcp_ubuntu]](#)                       | N/A


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
-   Daniel Bleichenbacher
-   William Conner
-   Thai Duong
-   Thomas Holenstein
-   Stefan Kölbl
-   Charles Lee
-   Cindy Lin
-   Fernando Lobato Meeser
-   Atul Luykx
-   Rafael Misoczki
-   Sophie Schmieg
-   Laurent Simon
-   Elizaveta Tretiakova
-   Jürg Wullschleger

Alumni:

-   Haris Andrianakis
-   Tanuj Dhir
-   Quan Nguyen
-   Bartosz Przydatek
-   Enzo Puig
-   Veronika Slívová
-   Paula Vidas
