# Python Cloud KMS digital signature example

This example shows how to sign and verify data with Tink using an asymmetric
signing key stored in [Google Cloud KMS](https://cloud.google.com/kms/docs).

The private key never leaves Cloud KMS: signing is performed by Cloud KMS via
the AsymmetricSign RPC. Verification fetches the public key from Cloud KMS once,
when the verifier is built, and is then performed locally with no further Cloud
KMS calls. Alternatively, verification can be performed offline using a
pre-fetched public key without any Cloud KMS calls.

The CLI takes the following arguments:

*   `--mode`: `sign`, `verify`, or `verify_offline` to indicate whether to sign,
    verify online, or verify offline with a pre-fetched public key.
*   `--key_name`: The resource name of the Cloud KMS `CryptoKeyVersion`, of the
    form
    `projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*`. Note
    that, unlike the AEAD key URIs, this is the bare KMS resource name and is
    *not* prefixed with `gcp-kms://`. Required for `sign` and `verify` modes.
*   `--gcp_credential_path`: Name of the file with the GCP credentials in JSON
    format. Required for `sign` and `verify` modes.
*   `--public_key_path`: Path to a file containing the pre-fetched public key
    (PEM or raw bytes). Required for `verify_offline` mode.
*   `--algorithm`: Name of the Cloud KMS `CryptoKeyVersionAlgorithm` (e.g.,
    `EC_SIGN_P256_SHA256`). Required for `verify_offline` mode.
*   `--data_path`: Read the input data from this file.
*   `--signature_path`: Write the signature to (sign) or read it from (verify /
    verify_offline) this file. The signature is written and read as a
    hex-encoded string.

## Prerequisite

This example uses a Cloud KMS asymmetric signing key. In order to run it, you
need to:

*   Create an
    [asymmetric signing key](https://cloud.google.com/kms/docs/create-key) on
    Cloud KMS. Copy the CryptoKeyVersion resource name, which is in this format:
    `projects/<my-project>/locations/global/keyRings/<my-key-ring>/cryptoKeys/<my-key>/cryptoKeyVersions/<version>`.

*   Create a service account that is allowed to sign with the above key and to
    fetch its public key (the `cloudkms.cryptoKeyVersions.useToSign` and
    `cloudkms.cryptoKeyVersions.viewPublicKey` permissions), and download a JSON
    credentials file.

## Build and Run

### Bazel

```shell
$ git clone https://github.com/tink-crypto/tink-py
$ cd tink-py/examples
$ bazel build ...
```

You can then sign a file:

```shell
$ echo "some data" > data.txt

# Replace the key name with your CryptoKeyVersion resource name, and
# my-service-account.json with your service account's credential JSON file.

$ ./bazel-bin/signature_kms/signature_kms_cli --mode sign \
    --key_name projects/<my-project>/locations/global/keyRings/<my-key-ring>/cryptoKeys/<my-key>/cryptoKeyVersions/1 \
    --gcp_credential_path my-service-account.json \
    --data_path data.txt \
    --signature_path signature.hex
```

Or verify the signature with:

```shell
$ ./bazel-bin/signature_kms/signature_kms_cli --mode verify \
    --key_name projects/<my-project>/locations/global/keyRings/<my-key-ring>/cryptoKeys/<my-key>/cryptoKeyVersions/1 \
    --gcp_credential_path my-service-account.json \
    --data_path data.txt \
    --signature_path signature.hex
```

Or verify the signature offline using a pre-fetched public key file (with no
Cloud KMS calls):

```shell
$ ./bazel-bin/signature_kms/signature_kms_cli --mode verify_offline \
    --public_key_path public_key.pem \
    --algorithm EC_SIGN_P256_SHA256 \
    --data_path data.txt \
    --signature_path signature.hex
```

### Pip package

```shell
$ git clone https://github.com/tink-crypto/tink-py
$ cd tink-py
$ pip3 install .[gcpkms]
```

You can then sign a file:

```shell
$ echo "some data" > data.txt
$ python3 signature_kms/signature_kms_cli.py --mode sign \
    --key_name projects/<my-project>/locations/global/keyRings/<my-key-ring>/cryptoKeys/<my-key>/cryptoKeyVersions/1 \
    --gcp_credential_path my-service-account.json \
    --data_path data.txt \
    --signature_path signature.hex
```

Or verify the signature offline using a pre-fetched public key file (with no
Cloud KMS calls):

```shell
$ python3 signature_kms/signature_kms_cli.py --mode verify_offline \
    --public_key_path public_key.pem \
    --algorithm EC_SIGN_P256_SHA256 \
    --data_path data.txt \
    --signature_path signature.hex
```
