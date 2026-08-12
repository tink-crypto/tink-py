# Python Cloud KMS MAC example

This example shows how to compute and verify a Message Authentication Code (MAC)
with Tink using a key stored in [Google Cloud KMS](https://cloud.google.com/kms/docs).

The key never leaves Cloud KMS: both MAC computation and verification are
forwarded to Cloud KMS via the `MacSign` and `MacVerify` RPCs.

The CLI takes the following arguments:

*   `--mode`: `compute` or `verify` to indicate whether to compute or verify a
    MAC.
*   `--key_name`: The resource name of the Cloud KMS `CryptoKeyVersion`, of the
    form
    `projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*`. Note
    that, unlike the AEAD key URIs, this is the bare KMS resource name and is
    *not* prefixed with `gcp-kms://`.
*   `--gcp_credential_path`: Name of the file with the GCP credentials in JSON
    format.
*   `--data_path`: Read the input data from this file.
*   `--mac_path`: Write the MAC to (for `compute`) or read it from (for `verify`) this file.

## Prerequisite

This example uses a Cloud KMS MAC key. In order to run it, you need to:

*   Create a [MAC signing key](https://cloud.google.com/kms/docs/create-key) on
    Cloud KMS. Copy the CryptoKeyVersion resource name, which is in this format:
    `projects/<my-project>/locations/global/keyRings/<my-key-ring>/cryptoKeys/<my-key>/cryptoKeyVersions/<version>`.

*   Create a service account that is allowed to compute and verify MACs with the
    above key (the `cloudkms.cryptoKeyVersions.useToSign` and
    `cloudkms.cryptoKeyVersions.useToVerify` permissions), and download a JSON
    credentials file.

## Build and Run

### Bazel

```shell
$ git clone https://github.com/tink-crypto/tink-py
$ cd tink-py/examples
$ bazel build ...
```

You can then compute a MAC over a file:

```shell
$ echo "some data" > data.txt

# Replace the key name with your CryptoKeyVersion resource name, and
# my-service-account.json with your service account's credential JSON file.

$ ./bazel-bin/mac_kms/mac_kms_cli --mode compute \
    --key_name projects/<my-project>/locations/global/keyRings/<my-key-ring>/cryptoKeys/<my-key>/cryptoKeyVersions/1 \
    --gcp_credential_path my-service-account.json \
    --data_path data.txt \
    --mac_path mac.hex
```

Or verify the MAC with:

```shell
$ ./bazel-bin/mac_kms/mac_kms_cli --mode verify \
    --key_name projects/<my-project>/locations/global/keyRings/<my-key-ring>/cryptoKeys/<my-key>/cryptoKeyVersions/1 \
    --gcp_credential_path my-service-account.json \
    --data_path data.txt \
    --mac_path mac.hex
```

### Pip package

```shell
$ git clone https://github.com/tink-crypto/tink-py
$ cd tink-py
$ pip3 install .[gcpkms]
```

You can then compute a MAC over a file:

```shell
$ echo "some data" > data.txt
$ python3 mac_kms/mac_kms_cli.py --mode compute \
    --key_name projects/<my-project>/locations/global/keyRings/<my-key-ring>/cryptoKeys/<my-key>/cryptoKeyVersions/1 \
    --gcp_credential_path my-service-account.json \
    --data_path data.txt \
    --mac_path mac.hex
```
