# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import textwrap
from typing import TypeAlias
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.api_core import exceptions as core_exceptions
from google.cloud import kms_v1
import google_crc32c

from tink import core
from tink.integration.gcpkms import _gcp_kms_util

_KEY_VERSION = 'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1'
_OTHER_KEY_VERSION = 'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/2'
_PUBLIC_KEY_DATA = (
    b'-----BEGIN PUBLIC KEY-----\nfake pem\n-----END PUBLIC KEY-----'
)

_Algorithm: TypeAlias = kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm

# An ML-DSA-65 algorithm OID and the corresponding raw public key size.
_ML_DSA_65_OID, _ML_DSA_65_KEY_SIZE = _gcp_kms_util.ML_DSA_EXTERNAL_MU_PARAMS[
    _Algorithm.PQ_SIGN_ML_DSA_65_EXTERNAL_MU
]

# A SubjectPublicKeyInfo whose subjectPublicKey is _ml_dsa_test_public_key,
# DER-encoded independently of pyasn1 by OpenSSL's own ASN.1generator.
# Regenerate with
# OpenSSL (>= 3.5, which supports ML-DSA):
#   HEX=$(python3 -c "print(bytes(i%251 for i in range(1952)).hex())")
#   cat > spki.cnf <<EOF
#   asn1=SEQUENCE:spki
#   [spki]
#   algorithm=SEQUENCE:algid
#   subjectPublicKey=FORMAT:HEX,BITSTRING:$HEX
#   [algid]
#   oid=OID:2.16.840.1.101.3.4.3.18
#   EOF
#   openssl asn1parse -genconf spki.cnf -out spki.der -noout
#   { echo "-----BEGIN PUBLIC KEY-----"; openssl base64 -in spki.der;
#     echo "-----END PUBLIC KEY-----"; }
_ML_DSA_65_OPENSSL_SPKI_PEM = textwrap.dedent("""\
    -----BEGIN PUBLIC KEY-----
    MIIHsjALBglghkgBZQMEAxIDggehAAABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZ
    GhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0hJ
    SktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5
    ent8fX5/gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5ydnp+goaKjpKWmp6ip
    qqusra6vsLGys7S1tre4ubq7vL2+v8DBwsPExcbHyMnKy8zNzs/Q0dLT1NXW19jZ
    2tvc3d7f4OHi4+Tl5ufo6err7O3u7/Dx8vP09fb3+Pn6AAECAwQFBgcICQoLDA0O
    DxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+
    P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1u
    b3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2e
    n6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3O
    z9DR0tPU1dbX2Nna29zd3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+foAAQID
    BAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIz
    NDU2Nzg5Ojs8PT4/QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl9gYWJj
    ZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXp7fH1+f4CBgoOEhYaHiImKi4yNjo+QkZKT
    lJWWl5iZmpucnZ6foKGio6SlpqeoqaqrrK2ur7CxsrO0tba3uLm6u7y9vr/AwcLD
    xMXGx8jJysvMzc7P0NHS09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz
    9PX29/j5+gABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fICEiIyQlJico
    KSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0hJSktMTU5PUFFSU1RVVldY
    WVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ent8fX5/gIGCg4SFhoeI
    iYqLjI2Oj5CRkpOUlZaXmJmam5ydnp+goaKjpKWmp6ipqqusra6vsLGys7S1tre4
    ubq7vL2+v8DBwsPExcbHyMnKy8zNzs/Q0dLT1NXW19jZ2tvc3d7f4OHi4+Tl5ufo
    6err7O3u7/Dx8vP09fb3+Pn6AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwd
    Hh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xN
    Tk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9
    fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6yt
    rq+wsbKztLW2t7i5uru8vb6/wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd
    3t/g4eLj5OXm5+jp6uvs7e7v8PHy8/T19vf4+foAAQIDBAUGBwgJCgsMDQ4PEBES
    ExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8PT4/QEFC
    Q0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl9gYWJjZGVmZ2hpamtsbW5vcHFy
    c3R1dnd4eXp7fH1+f4CBgoOEhYaHiImKi4yNjo+QkZKTlJWWl5iZmpucnZ6foKGi
    o6SlpqeoqaqrrK2ur7CxsrO0tba3uLm6u7y9vr/AwcLDxMXGx8jJysvMzc7P0NHS
    09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+gABAgMEBQYH
    CAkKCwwNDg8QERITFBUWFxgZGhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3
    ODk6Ozw9Pj9AQUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZn
    aGlqa2xtbm9wcXJzdHV2d3h5ent8fX5/gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaX
    mJmam5ydnp+goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2+v8DBwsPExcbH
    yMnKy8zNzs/Q0dLT1NXW19jZ2tvc3d7f4OHi4+Tl5ufo6err7O3u7/Dx8vP09fb3
    +Pn6AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKiss
    LS4vMDEyMzQ1Njc4OTo7PD0+P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltc
    XV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn+AgYKDhIWGh4iJiouM
    jY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq+wsbKztLW2t7i5uru8
    vb6/wMHC
    -----END PUBLIC KEY-----""").encode('utf-8')


def _ml_dsa_test_public_key(size: int) -> bytes:
  """Returns deterministic bytes of the given size to stand in for a raw key."""
  return bytes(i % 251 for i in range(size))


def _public_key_response(
    name: str = _KEY_VERSION,
    algorithm: kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm = _Algorithm.EC_SIGN_P256_SHA256,
    data: bytes = _PUBLIC_KEY_DATA,
    crc32c_checksum: int | None = None,
) -> kms_v1.types.PublicKey:
  if crc32c_checksum is None:
    crc32c_checksum = google_crc32c.value(data)
  return kms_v1.types.PublicKey(
      name=name,
      algorithm=algorithm,
      public_key=kms_v1.types.ChecksummedData(
          data=data, crc32c_checksum=crc32c_checksum
      ),
  )


class CustomException(core_exceptions.GoogleAPIError):
  pass


class ValidateKmsKeyNameTest(parameterized.TestCase):

  def test_valid_key_name_passes(self):
    self.assertIsNone(_gcp_kms_util.validate_kms_key_name(_KEY_VERSION))

  @parameterized.parameters(
      '',
      None,
      'wrong/kms/key/format',
      # A CryptoKey is not enough; a CryptoKeyVersion is required.
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1',
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions',
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1/',
      'gcp-kms://projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1',
  )
  def test_invalid_key_name_fails(self, key_name):
    with self.assertRaisesRegex(
        core.TinkError, r'key_name cannot be null|Invalid key_name format'
    ):
      _gcp_kms_util.validate_kms_key_name(key_name)


class FetchPublicKeyTest(parameterized.TestCase):

  def test_pem_success_returns_key(self):
    client = mock.Mock()
    client.get_public_key.return_value = _public_key_response()

    response = _gcp_kms_util.fetch_public_key(client, _KEY_VERSION)

    self.assertEqual(response.name, _KEY_VERSION)
    self.assertEqual(client.get_public_key.call_count, 1)
    request = client.get_public_key.call_args.kwargs['request']
    self.assertEqual(
        request.public_key_format, kms_v1.PublicKey.PublicKeyFormat.PEM
    )

  def test_response_key_name_mismatch_fails(self):
    client = mock.Mock()
    client.get_public_key.return_value = _public_key_response(
        name=_OTHER_KEY_VERSION
    )
    with self.assertRaisesRegex(
        core.TinkError,
        r'The key name in the GetPublicKey response does not match',
    ):
      _gcp_kms_util.fetch_public_key(client, _KEY_VERSION)

  def test_checksum_mismatch_fails(self):
    client = mock.Mock()
    client.get_public_key.return_value = _public_key_response(crc32c_checksum=1)
    with self.assertRaisesRegex(
        core.TinkError, r'The GetPublicKey checksum does not match'
    ):
      _gcp_kms_util.fetch_public_key(client, _KEY_VERSION)

  def test_falls_back_to_nist_pqc(self):
    client = mock.Mock()
    client.get_public_key.side_effect = [
        CustomException(
            'Only NIST_PQC format is supported for this algorithm.'
        ),
        _public_key_response(algorithm=_Algorithm.PQ_SIGN_SLH_DSA_SHA2_128S),
    ]

    response = _gcp_kms_util.fetch_public_key(client, _KEY_VERSION)

    self.assertIsNotNone(response)
    self.assertEqual(client.get_public_key.call_count, 2)
    request = client.get_public_key.call_args.kwargs['request']
    self.assertEqual(
        request.public_key_format, kms_v1.PublicKey.PublicKeyFormat.NIST_PQC
    )

  def test_non_pem_error_not_retried_fails(self):
    client = mock.Mock()
    client.get_public_key.side_effect = CustomException('some other error')
    with self.assertRaisesRegex(core.TinkError, r'some other error'):
      _gcp_kms_util.fetch_public_key(client, _KEY_VERSION)
    self.assertEqual(client.get_public_key.call_count, 1)

  def test_nist_pqc_retry_fails(self):
    # The PEM request signals NIST_PQC-only, but the NIST_PQC retry itself
    # fails; the retry error is surfaced.
    client = mock.Mock()
    client.get_public_key.side_effect = [
        CustomException(
            'Only NIST_PQC format is supported for this algorithm.'
        ),
        CustomException('nist pqc retry boom'),
    ]
    with self.assertRaisesRegex(core.TinkError, r'nist pqc retry boom'):
      _gcp_kms_util.fetch_public_key(client, _KEY_VERSION)
    self.assertEqual(client.get_public_key.call_count, 2)


class ParseSpkiPemTest(parameterized.TestCase):

  def test_valid_pem_returns_spki(self):
    spki = _gcp_kms_util.parse_spki_pem(_ML_DSA_65_OPENSSL_SPKI_PEM)
    self.assertIsNotNone(spki)
    self.assertEqual(str(spki['algorithm']['algorithm']), _ML_DSA_65_OID)

  def test_content_outside_markers_is_discarded(self):
    spki = _gcp_kms_util.parse_spki_pem(_ML_DSA_65_OPENSSL_SPKI_PEM)
    padded_pem = (
        b'preamble to ignore\n'
        + _ML_DSA_65_OPENSSL_SPKI_PEM
        + b'\ntrailing to ignore'
    )
    self.assertEqual(
        _gcp_kms_util.parse_spki_pem(padded_pem),
        spki,
    )

  def test_malformed_pem_fails(self):
    pem = (
        b'-----BEGIN PUBLIC KEY-----\n'
        + base64.b64encode(b'not a valid spki')
        + b'\n-----END PUBLIC KEY-----'
    )
    with self.assertRaisesRegex(
        core.TinkError, r'Failed to parse the public key PEM'
    ):
      _gcp_kms_util.parse_spki_pem(pem)

  @parameterized.named_parameters(
      (
          'not_a_public_key',
          (
              b'-----BEGIN CERTIFICATE-----\n'
              + base64.b64encode(b'body')
              + b'\n-----END CERTIFICATE-----'
          ),
      ),
      (
          'missing_begin',
          base64.b64encode(b'body') + b'\n-----END PUBLIC KEY-----',
      ),
      (
          'missing_end',
          b'-----BEGIN PUBLIC KEY-----\n' + base64.b64encode(b'body'),
      ),
      (
          'mismatched_boundary',
          (
              b'-----BEGIN PUBLIC KEY-----\n'
              + base64.b64encode(b'body')
              + b'\n-----END CERTIFICATE-----'
          ),
      ),
      (
          'header_field',
          (
              b'-----BEGIN PUBLIC KEY-----\nProc-Type: 4,ENCRYPTED\n'
              + base64.b64encode(b'body')
              + b'\n-----END PUBLIC KEY-----'
          ),
      ),
      (
          'invalid_base64',
          (
              b'-----BEGIN PUBLIC KEY-----\n'
              b'not!!!valid???base64\n'
              b'-----END PUBLIC KEY-----'
          ),
      ),
  )
  def test_invalid_pem_structure_fails(self, pem: bytes):
    with self.assertRaisesRegex(
        core.TinkError, r'Failed to parse the public key PEM'
    ):
      _gcp_kms_util.parse_spki_pem(pem)


class ExtractRawMlDsaPublicKeyTest(parameterized.TestCase):

  def test_valid_pem_returns_raw_key(self):
    raw_public_key = _ml_dsa_test_public_key(_ML_DSA_65_KEY_SIZE)
    pem = _gcp_kms_util.raw_ml_dsa_public_key_to_pem(
        _ML_DSA_65_OID, raw_public_key
    )

    self.assertEqual(
        _gcp_kms_util.extract_raw_ml_dsa_public_key(
            pem, _ML_DSA_65_OID, _ML_DSA_65_KEY_SIZE
        ),
        raw_public_key,
    )

  def test_wrong_key_size_fails(self):
    # The raw key is one byte shorter than expected.
    pem = _gcp_kms_util.raw_ml_dsa_public_key_to_pem(
        _ML_DSA_65_OID, bytes(_ML_DSA_65_KEY_SIZE - 1)
    )
    with self.assertRaisesRegex(core.TinkError, r'Incorrect public key size'):
      _gcp_kms_util.extract_raw_ml_dsa_public_key(
          pem, _ML_DSA_65_OID, _ML_DSA_65_KEY_SIZE
      )

  def test_wrong_oid_fails(self):
    # The OID of ML-DSA-87 does not match the expected ML-DSA-65 OID.
    wrong_oid, _ = _gcp_kms_util.ML_DSA_EXTERNAL_MU_PARAMS[
        _Algorithm.PQ_SIGN_ML_DSA_87_EXTERNAL_MU
    ]
    pem = _gcp_kms_util.raw_ml_dsa_public_key_to_pem(
        wrong_oid, bytes(_ML_DSA_65_KEY_SIZE)
    )
    with self.assertRaisesRegex(core.TinkError, r'Unexpected public key OID'):
      _gcp_kms_util.extract_raw_ml_dsa_public_key(
          pem, _ML_DSA_65_OID, _ML_DSA_65_KEY_SIZE
      )

  def test_openssl_generated_pem_returns_raw_key(self):
    # The PEM is DER-encoded by OpenSSL rather than pyasn1, so this also checks
    # interoperability with a real-world encoder, not just a pyasn1 round-trip.
    self.assertEqual(
        _gcp_kms_util.extract_raw_ml_dsa_public_key(
            _ML_DSA_65_OPENSSL_SPKI_PEM, _ML_DSA_65_OID, _ML_DSA_65_KEY_SIZE
        ),
        _ml_dsa_test_public_key(_ML_DSA_65_KEY_SIZE),
    )


class RawMlDsaPublicKeyToPemTest(parameterized.TestCase):

  def test_encodes_valid_pem(self):
    raw_public_key = _ml_dsa_test_public_key(_ML_DSA_65_KEY_SIZE)
    pem = _gcp_kms_util.raw_ml_dsa_public_key_to_pem(
        _ML_DSA_65_OID, raw_public_key
    )

    self.assertTrue(pem.startswith(b'-----BEGIN PUBLIC KEY-----\n'))
    self.assertTrue(pem.endswith(b'\n-----END PUBLIC KEY-----'))
    for line in pem.decode().splitlines():
      self.assertLessEqual(len(line), 64)
    self.assertEqual(
        _gcp_kms_util.extract_raw_ml_dsa_public_key(
            pem, _ML_DSA_65_OID, _ML_DSA_65_KEY_SIZE
        ),
        raw_public_key,
    )


if __name__ == '__main__':
  absltest.main()
