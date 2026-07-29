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
from tink.integration.gcpkms import _gcp_kms_public_key_verify

_KEY_VERSION_NAME = 'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1/cryptoKeyVersions/1'

_MESSAGE = b'data'

_Algorithm: TypeAlias = kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm


# Generated with
# $ openssl ec -in ecdsa-private.pem -pubout -out ecdsa-public.pem
# after generating the private key with
# $ openssl ecparam -name prime256v1 -genkey -noout -out ecdsa-private.pem
_ECDSA_P256_PEM = textwrap.dedent("""\
    -----BEGIN PUBLIC KEY-----
    MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEPu+j4MR6Veo9F2YyKq0AObMM3UoN
    K4Z6V0tej/9smL+QfqkILtkY0DROmBbLb/tOg+zi/q6CAG5FuBK7CaZP0g==
    -----END PUBLIC KEY-----
    """).encode('utf-8')
# Generated with
# $ openssl ec -in ecdsa-private.pem -pubout -out ecdsa-public.pem
# after generating the private key with
# $ openssl ecparam -name secp384r1 -genkey -noout -out ecdsa-private.pem
_ECDSA_P384_PEM = textwrap.dedent("""\
    -----BEGIN PUBLIC KEY-----
    MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAEvhSzPPgaNlVa7ALdPv2TU/y7zcztJKMW
    Uyb4EFljhW+HwMedJ9rq58P9vCO81GK+uzMElfKXwyh9Hwki3OrHw/U/QpEHrYAc
    mjodwJBbZu8a/6Oc2bXN96IwqOhAM70l
    -----END PUBLIC KEY-----
    """).encode('utf-8')
# Generated with
# $ openssl rsa -in rsa-private.pem -pubout > rsa-public.pem
# after generating the private key with
# $ openssl genrsa -out rsa-private.pem 2048
_RSA_2048_PEM = textwrap.dedent("""\
    -----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnWdm/pltnPoPL7V+vQzI
    YO0xm4d9lTBdWHWyvWIwFbG9ePPI2DS5bAUREY8pW/L7FzhHGvgrkuLgIFP8WTYd
    4fm1L+QhhSIIltdnW8IeZobRsmrnz8oN/U6VPN8wGgPUzv1MM/vWQcNfDvv5E/kw
    sJAD1e+V6S2rts2f8zFHHP71vXITSumOaVvJTVHZgyWEXA63C2MEQVMhzXrsnJua
    5JY9TDAhFHDRiKzng9ZSbRmItutY8+FdlmoZVjWnFnhdloVvn/KzSjv0FmmHwmAI
    Tt1aTrN7iWBoy/YBL61yxMMr91gtWh5Dp6KXYErYxS6v5fh5VOmrYJCeMugyokIW
    zQIDAQAB
    -----END PUBLIC KEY-----
    """).encode('utf-8')
# Generated with
# $ openssl rsa -in rsa-private-3072.pem -pubout > rsa-public-3072.pem
# after generating the private key with
# $ openssl genrsa -out rsa-private-3072.pem 3072
_RSA_3072_PEM = textwrap.dedent("""\
    -----BEGIN PUBLIC KEY-----
    MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAi9Q2UorCOwp7Y5r+qO0n
    mdlz8/GLQ1dh+9XR/wtL2uMGwEbTyziFt3UocxlxZLw6dQtHY3xfMW37lpRX5PFt
    T68SeWRh+Cz+6i75NKa+FHrYM4d/HLYjFk+vOw75GIVfe0epi3UdMs5Ob8LGqaKP
    PF6uPk/PSEJvXZ78Is2yODuUCecV0aDajQ/873jdwBrzXuaqG9SpLf8UTg891nuS
    P+yZ075LvUu3ylcDxFsWclenATML3sgkrW1qQJKW5/UXRUQGNNnBPqF2EgIUlc6E
    N8RszNjWKtzbs4EKirHd881Naw656nM/KfLj+00g0Vfd3/lvi2o8YFbDKcnKYZfI
    tdohx9Zt4b3slCZOF/zMlvPKCn9tpa17A7rCBv57I80/+evKaq5PX84G+UcfV5kz
    LHi+FNXBtJLzYr8JKxkad4U2ecjrK1jjvJtuPbqYosKCpRfBGsy3CdfeYn2xTtDZ
    s+l73QYpWpnXUyjydhsTafQY0dce6azjrvmRWGFoSSRHAgMBAAE=
    -----END PUBLIC KEY-----
    """).encode('utf-8')
# Generated with
# $ openssl rsa -in rsa-private-4096.pem -pubout > rsa-public-4096.pem
# after generating the private key with
# $ openssl genrsa -out rsa-private-4096.pem 4096
_RSA_4096_PEM = textwrap.dedent("""\
    -----BEGIN PUBLIC KEY-----
    MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA1GeEVEj1xv0ppPMAVMmK
    PIsx7xt/6lyM2I9Am11HDVZ8+pN9FgGb7hMIXqBQWWhLCStvLBJPSlv+RUsw1GK4
    3MD+Yxlc4X132KaC/Z6qIf+aD5FthfETtTEJem7HCTCSEyJXoeXYu69NrN9e+m+V
    bcIVFaZ+f31tiDtSZi7fTCVbmSGG9WeqKZe/hKuhOan8lH2IJmxFjOk9hKFVqxB0
    wTMFw7enAwLJxDqQMFXVK8zgjfvJ147AIol96VbS7si9Lnff9TfNjzcGfe1hsXNP
    g10gLFu2N2LmjD9sb1gfWJGSGTsJiyX/owu+jj7GCWyQhY6hFTvZKbE0c1ZFLYbv
    IiUBYJZUBk58iFgO7WA+fync9jDN9nNlw68e3xnqF7iherDS7IqZ5x8d+b+wgJKy
    pBJI5hYY3OJB2yp4Ao9K4wQFxvJBBpg3jCGoofVVjrA8lePa3Yb8EHy+z5u5mYNj
    VSxw8SXzqNsAgl5aW6c7Gs1c7m+Hpfdi4K+OJl60H0eYF+ks0KVShNRYri6q347D
    IVpX3Qc6YOGPUHUj9lX7NfFJseGzbiJYTOQ+kVxvCmUqKMfq1vLvkgEfTpK53pTy
    Z8h8oIZLTJo4MPwFbQAWNcKBGh43fMLWVWCED64N1S/2qNVv1R90OCerKLaX8WdY
    txOSq3pgn5BD2tHhZ7ZmxTsCAwEAAQ==
    -----END PUBLIC KEY-----
    """).encode('utf-8')

# Generated with
# $ echo -n "data" | openssl dgst -sha256 -sign ecdsa-private.pem | base64
_ECDSA_P256_SHA256_SIG = base64.b64decode(
    'MEUCIQD1n5HhsGwZ4hU2LVqTnUqQLlGidxPVVUBPbg8W1FGm4QIgQtSebi2H9/EZPKSs'
    'qYnkIFtszI4jNZYWfcOFOjtJi7o='
)
# Generated with
# $ echo -n "data" | openssl dgst -sha384 -sign ecdsa-private.pem | base64
_ECDSA_P384_SHA384_SIG = base64.b64decode(
    'MGUCMEJreAXQPgGuVKNEctuQRAh8sbdWbnxwbOIERx6A7KrXfx/VIGYsEIX9OjIgNGc+'
    'pwIxAOVNn7DccgsZjhOwaL+HsI0RqbBFxRIaLQjlO9JT5BWxbsRX/7nio7krXpcfXFhn'
    'Dg=='
)
# Generated with
# $ echo -n "data" | openssl dgst -sha256 -binary | openssl pkeyutl -sign \
#     -inkey rsa-private.pem \
#     -pkeyopt digest:sha256 -pkeyopt rsa_padding_mode:pkcs1 | base64
_RSA_PKCS1_2048_SHA256_SIG = base64.b64decode(
    'NI2jo+WIrKjoyIR/jtlSBT0BJJJ0aDgIi86rXVOqPq35DyULjT1JwtKvgtqocNaeeKDQ'
    '4HRQhNKnZYeDzQO6nHD6SgngAv0v9FBGTph4VUNZ0To1Bzlk8LP+P/0PWWy59aAHzAFU'
    'LCiU7/6nP2KSInbRvg7UmMRXcfw956D3skFZn2dbu/xCRhYuZCiej72s6sNVRC1dHpIB'
    'z2+/f7ux4/gJgiYJGC9bvmkRDzZIy7e3zf1Be7ZT/zAreAbL+Zk8BEvoWItV0YkDUs33'
    'MkFY1MCR44grai6fGGOJAxgahlcgvkueO3tnao5epghHnwamS9I2h8zcBe984Z0MR+NX'
    'fw=='
)
# Generated with
# $ echo -n "data" | openssl dgst -sha256 -binary | openssl pkeyutl -sign \
#     -inkey rsa-private-3072.pem  \
#     -pkeyopt digest:sha256 -pkeyopt rsa_padding_mode:pkcs1 | base64
_RSA_PKCS1_3072_SHA256_SIG = base64.b64decode(
    'iPyX74OCyZOh7GO7Y1UI3ucb8OMb9LoiIjHrW4jFKpS/aLjDGXrjEFbfsF3JITOFfOWx'
    '3M8+jIGs4wwmHWiWCufqkbf4gtndGAoaEddeK2ph8tqXEnzkq8o5qDk175ffeZYmVI7/'
    'vi5xwc2oz5kd17wfCD0MmFGxLef1C22Wz+MJTRi0LX6Ngsy/vR4Fx5N7+EXDdqPYx2ZL'
    'IhyQvXd7GztFxZTa8s7yQ6Grq2oslO13aMiu1dC9y9QYWLoY4uhF0te2WJerW5lRUp+0'
    '0pk2ruC/yTaLXwS3bFZFx4FmNTClQCC/JLugNekKJv9/FXex/L6muQseXxfezRiKV3fY'
    '2Ee7qxngZZZ/EU/TIDqBN3q3dE0eCyA/A2Ox7xtxQqyTeIDeURZN9j5YtaVffp47oV2M'
    '0pSHTmcIyIwhHLx0MqWUPGUP3NvpjclNCeC5L8YieQKJiEBleoLpVA4nc2KEEdHyb+pF'
    'paN+Pvw2V8X29uRl7ZIAkzxbnbaog7p3xza8'
)
# Generated with
# $ echo -n "data" | openssl dgst -sha256 -binary | openssl pkeyutl -sign \
#     -inkey rsa-private-4096.pem  \
#     -pkeyopt digest:sha256 -pkeyopt rsa_padding_mode:pkcs1 | base64
_RSA_PKCS1_4096_SHA256_SIG = base64.b64decode(
    'cqJsTB70moE9s+3OElRbmLFFXkRIYU0TKuhL+y8UMr/XUOqcXdrynnionthm6DJm681T'
    'J88eHN29eeZiyTt1UtQZBbMjAUOdrhcndHNdoxfQuVPJ8a4HuMOWXTT6B2ewxNDrWjhJ'
    'Z2PARPBnl3OR1JWex8ynj7gIPFcsW6+pVDilMmxRkHHxj3xKplQ+uYRlY9ifggcs/ujx'
    '+UxZcScicfZWTbNuGlmddN6+IV6q++gW7VoU+OZSaLBttFU93ohkLNnFYjRF1JxdKXNz'
    'OciJ7/AHtDd/XJ2zqnJsJCm0G/GkK+UBW3lTkFcWjaqEqQEFKxVygIWIQsKF760BoZDk'
    'TgeSFeSo0aUAFG3WlKFoDQKQUVVgoKq0cU+VMqinvfAunEHJAmq4An9IcxX3As8gyGBy'
    'HO5xfoXwRrQfrJunRGWPvp5MXFm+i53FkfkDs1+DtypSKkX0BrCSu1uRmIZxt0MhgJWg'
    'vQdXtglH3y4b7bmFOG/dvyGhMoSSpfRdjulPL/P5jW+zlDdwpr8WtrnYRC0m4X8YpiBh'
    'XojYd1rtne5Q+A8t8EKNt2SXPadhSsRPoNF5wgD9tkoTvE0SbbdUm59c+cp9Hdj+oJTW'
    'hYtpAcC+p6WebsZ9ILE180j44RRMF9GRk34AiDhr5bOwR+EEi8ScMj7LQhb+lcfQKwYr'
    '0EU='
)
# Generated with
# $ echo -n "data" | openssl dgst -sha512 -binary | openssl pkeyutl -sign \
#     -inkey rsa-private-4096.pem  \
#     -pkeyopt digest:sha512 -pkeyopt rsa_padding_mode:pkcs1 | base64
_RSA_PKCS1_4096_SHA512_SIG = base64.b64decode(
    'lq3wThF4Xa99ICz0vsTSBMa+uUclsECaUetUmLDvB/zjmHBIzeFrf6l0b/OtF9gnqq35'
    'nbvnJlaC8vCZJMYfiGahkUfi7Vqw4sxxCfmBTbN+F8bl4n0dV+Na00pNHgRNKLaOcsty'
    'vBC74DD4e3mM799T3nOELe8ASUCa0jGlVDhrSIQVt1wnfNZktrLWRjWm+cCz9w5RXira'
    '2fqz3/sDQbG6AcpJ8SzsfBd4/52sQTRtrIDs2T+0BEku77rFozXMhO0ttkVsFijNsUr0'
    'R+FG3/gkPVBbMJl5ClCJw7qifsTsdw0MiCunp6lvAm9CAz5AZMjA+iFgFSILaPLTFHy8'
    'Z5kFLcTqhgHcQAgqGGlhiucuuXruO+b907GyQ4txqWtWVuWmNWVgC9HAh3ra1tN7SgLj'
    '7cKFABq1GqNzkp6bDMtjutr8GfXMmIG/at4Uj9pmlpe+1ob1dEFU8Oq/xdnrATTIzagq'
    'HrHqMSLqZ4/vXwwaDoIDDlR3tULV9/pPhh+60F4z8c4SbDSPOHTMxT3fRtxO+ko9JZmk'
    'a5PaGnjtNQVc16XYTR+23asReB6gcIu2xvvIhxtxASANdg5Nk+L/M6IZeFx0hnGOB4AV'
    'Q2YF8IJ58A1rr9tT41MtyaPhGjOTNuFPlnyAJ5V/CalwuAtGFq5fMokC+AzcL4p9KruI'
    'odE='
)
# Generated with
# $ echo -n "data" | openssl pkeyutl -sign -inkey rsa-private-4096.pem
#     openssl pkeyutl -sign -inkey rsa-private.pem -pkeyopt digest:sha256 \
#     -pkeyopt rsa_padding_mode:pss -pkeyopt rsa_pss_saltlen:32 | base64
_RSA_PSS_2048_SHA256_SIG = base64.b64decode(
    'FhypcoCQT2X/9tn3qo7s9GSFjPew41hV2OveWlAwElYzke4dlfVIrpgnfpjOMHJuD2BI'
    'Jc7ePKi2XPTS+QS3LmWx8Qv4wKUgdluDK0ZD+Dm2MAHfYaLq3J3LqJhjOkcnM2KuYJcU'
    'Fj40edYkhwg1oYUc4EEKrSIh72Px6GGJa0nbRuCYx9vm7eH5zx/M4wIpOF+ScczoL6Lk'
    'OyX8hFB2Ub9LxBh3OPahe/zTQKy0+gMjUGqjwTxq3EBlkngY0LWh2fE+COhoq6mAddVi'
    'yVfJjHCApY1KZXPWgg5tzbpttmDf6yKTStTyAxt686GkeWL0kUzsmkGDQB1Ld6WJ+5KN'
    'lQ=='
)
# Generated with
# echo -n "data" | openssl dgst -sha256 -binary |
#      openssl pkeyutl -sign -inkey rsa-private-3072.pem
#      -pkeyopt digest:sha256 -pkeyopt rsa_padding_mode:pss
#      -pkeyopt rsa_pss_saltlen:32 | base64
_RSA_PSS_3072_SHA256_SIG = base64.b64decode(
    'aM6ZNE2qRKuxc2Mdehc3Uju9eE8U4C9687M2keVOiHEeDCUo1uJJmBOPYJI8MM1h2G+K'
    'CMdy0006zNuLGhANYASmplSCJfiI6eEJRhAgcX2km9VGeIF07VH+X0ZrdxTKX9hq4RnQ'
    'L+NiAnhcDjmYfNF1F+W86JjXt1QhWVPwCt0EhxC0dC41WyvM8a7r5e6P6VymkplCUuMI'
    'bnwNU4HtYyuc3HJnOgEODnrwZ8jlNuHEHM0v7LEzYTcUXtmC/IhLYloxqOPVechEy0TZ'
    'YC3Ir3rxa8JduTPCPnrYLsWRRUAchYIh5eS+f4KHWSvZ8zPdjt18VouLTKZMhNRB/Rlg'
    'V3SH8Ic3OVCoy979piJDyu9DGCRVZ5VoLH4VuhkdF5InvIzt7Lq5ApkF1JlKVM1V328P'
    'arbgGu0H+klCown/mD9sruFzJIzCat9wbX9gOMJAVSaZ6ZCKXeLIF+aVe8kOxayniAul'
    'OzbK1xatXChSQk6vtg1egFu4XkwhI7C9IWDG'
)
# echo -n "data" | openssl dgst -sha256 -binary |
#      openssl pkeyutl -sign -inkey rsa-private-4096.pem
#      -pkeyopt digest:sha256 -pkeyopt rsa_padding_mode:pss
#      -pkeyopt rsa_pss_saltlen:32 | base64
_RSA_PSS_4096_SHA256_SIG = base64.b64decode(
    'WMEq0q7+U24gx2SOwzWRI0M7aoYAvpQnz5kPMKRA4Ortn0bcJIsKXy4g4facoLygo+hJ'
    '4KiMmCQPsbNoz/3hgfQcTc5XfPAVbkBkT3nnYcY77wib1f/VSQpdObcAs4bE7EyQrXUB'
    '4fkIdQlj96GvreP6Vak0xjpSEdv0mA2rXuPWKsXUObsX1Wkto3Kz5DNplzxO2ofroo3V'
    'L8Lu3jv3OHH+c/fc9mKO5LRW4nIaf6n8IkNq7zR2OioN3461+Uhc+5PpFBy9SCpdWJml'
    'CYstN13Z8OLRi5zYhq8J8JBtJh1RkFDomNrEbkGKDd+VIgbuYpS7zRtJRFuBcHBrOorT'
    'Ly84YWOW5xIn1HeWax/mPneUs+gJk4Eu7wGaFDyhpJiLhw99AFn7b+Q2hCaQm+6/SW1Y'
    'jBqKPX7Sd9JTjadsTO+t/3kEI31TN/2MTTAkTuRYswgm8dBsRXmKMGJmzC7SIMxg0+tm'
    'uVkwbz2CPnv5CLSH9F6MuN1uynSWCzurOkyQUAy6J/A49EO/EPm+HY1WF29Oz+3Hn++C'
    'DnBoB9fKorFWgqD0j6qwK6JDzT9e7Dn0Cp+EhbffU0BBYM0F6YgmbGN7Kf7XnrsYywVS'
    '6k6dmdkTzFWyRWszkfBNW3iTaOraGuEvQ8qi/93vNUFefGqDg0Mn7pm2bVL0Dukpc5Rp'
    'Rjg='
)
# Generated with
# echo -n "data" | openssl dgst -sha512 -binary |
#      openssl pkeyutl -sign -inkey rsa-private-4096.pem
#      -pkeyopt digest:sha512 -pkeyopt rsa_padding_mode:pss
#      -pkeyopt rsa_pss_saltlen:64 | base64
_RSA_PSS_4096_SHA512_SIG = base64.b64decode(
    'zMztdsH/VYhGe32DCt3aSn9gUhzPREQhkMUi6bCHTzdV9wrN2yuAPCWRmBPymXh2tB7c'
    'hB/gbJWUYQeXYZtBgRnJKaPHhtQpeDFJwzbJt2eIiFA9RthLbo9kg1U9VuiXqfjKmkbj'
    '8Z5qbyJXVdl4f6hhAi2aGXaEpliRPLRUyuJRIIOU4O8clTQAoHqHCOLNtfpYU2LSABL6'
    'nM9awf/OGD98SFJ7sLwBDtB0b7imZxBYayf0E1h1pza8XdHVYmTxQ+jdc5nYk+G27AzU'
    '0SZUviB5tdAt62xtFZiRi6vkk7FgfY+m1jqv9FmklOiBuuZDPjdfQ1zlYTLdQHrGVCgO'
    '9jenC+OkeVyKOPmVgvETBsSEkr/W7kf2OM84mksymO10c0xqTCOi/cJd6zUYmi5IksU8'
    'DXQ1y8ZABzSoqIlRsOmyRQiW0CH+HmFl8HgtwZ9cSiKYtzagI5QnFhvzpt3/fI52HeAe'
    'bUFsd9x4xNmvcDkdXTO/cHCJXSRRO88LKBtuKZHgiXEfyQubEcTKMJxeQ1sM0efzF/Br'
    '3aylzgzd+a5KvMq/0WGoVmHgvrH41lVxIlL2K1MHopfWz1Qi9sFVyB3MmIXIpcSLGGYP'
    'gxL+zvqtZL+01ury1ASUw28414i4LU7OUO3C1oQc/tR4eETXYZ++qSsS6XmT7Br8k7h1'
    'VpQ='
)

# Maps each supported classical algorithm to (public key PEM, signature).
_TEST_VECTORS = {
    _Algorithm.EC_SIGN_P256_SHA256: (_ECDSA_P256_PEM, _ECDSA_P256_SHA256_SIG),
    _Algorithm.EC_SIGN_P384_SHA384: (_ECDSA_P384_PEM, _ECDSA_P384_SHA384_SIG),
    _Algorithm.RSA_SIGN_PKCS1_2048_SHA256: (
        _RSA_2048_PEM,
        _RSA_PKCS1_2048_SHA256_SIG,
    ),
    _Algorithm.RSA_SIGN_PKCS1_3072_SHA256: (
        _RSA_3072_PEM,
        _RSA_PKCS1_3072_SHA256_SIG,
    ),
    _Algorithm.RSA_SIGN_PKCS1_4096_SHA256: (
        _RSA_4096_PEM,
        _RSA_PKCS1_4096_SHA256_SIG,
    ),
    _Algorithm.RSA_SIGN_PKCS1_4096_SHA512: (
        _RSA_4096_PEM,
        _RSA_PKCS1_4096_SHA512_SIG,
    ),
    _Algorithm.RSA_SIGN_PSS_2048_SHA256: (
        _RSA_2048_PEM,
        _RSA_PSS_2048_SHA256_SIG,
    ),
    _Algorithm.RSA_SIGN_PSS_3072_SHA256: (
        _RSA_3072_PEM,
        _RSA_PSS_3072_SHA256_SIG,
    ),
    _Algorithm.RSA_SIGN_PSS_4096_SHA256: (
        _RSA_4096_PEM,
        _RSA_PSS_4096_SHA256_SIG,
    ),
    _Algorithm.RSA_SIGN_PSS_4096_SHA512: (
        _RSA_4096_PEM,
        _RSA_PSS_4096_SHA512_SIG,
    ),
}


def _public_key_response(
    name: str = _KEY_VERSION_NAME,
    algorithm: _Algorithm = _Algorithm.EC_SIGN_P256_SHA256,
    data: bytes = _ECDSA_P256_PEM,
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


class _MockGoogleApiError(core_exceptions.GoogleAPIError):
  pass


class GcpKmsPublicKeyVerifyTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_kms_client_cls = self.enter_context(
        mock.patch.object(kms_v1, 'KeyManagementServiceClient', autospec=True)
    )
    self.mock_client = self.mock_kms_client_cls.return_value

  @parameterized.parameters(*_TEST_VECTORS.items())
  def test_verify_succeeds(self, algorithm, vector):
    pem, sig = vector
    self.mock_client.get_public_key.return_value = _public_key_response(
        algorithm=algorithm, data=pem
    )
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
        _KEY_VERSION_NAME, self.mock_client
    )
    self.assertIsNone(verifier.verify(sig, _MESSAGE))

  @parameterized.parameters(*_TEST_VECTORS.items())
  def test_verify_no_rpc_succeeds(self, algorithm, vector):
    pem, sig = vector
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
        pem, algorithm
    )
    self.assertIsNone(verifier.verify(sig, _MESSAGE))

  @parameterized.parameters(*_TEST_VECTORS.items())
  def test_verify_wrong_data_fails(self, algorithm, vector):
    pem, sig = vector
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
        pem, algorithm
    )
    with self.assertRaises(core.TinkError):
      verifier.verify(sig, b'wrong data')

  @parameterized.parameters(*_TEST_VECTORS.items())
  def test_verify_wrong_signature_fails(self, algorithm, vector):
    pem, sig = vector
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
        pem, algorithm
    )
    # Flip the last byte of the signature.
    wrong_signature = sig[:-1] + bytes([sig[-1] ^ 0x01])
    with self.assertRaises(core.TinkError):
      verifier.verify(wrong_signature, _MESSAGE)

  def test_client_null(self):
    with self.assertRaisesRegex(core.TinkError, r'kms_client cannot be null'):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
          _KEY_VERSION_NAME, None
      )

  @parameterized.parameters(
      '',
      None,
      'wrong/kms/key/format',
      'projects/p1/locations/global/keyRings/kr1/cryptoKeys/ck1',
  )
  def test_key_name_format_wrong(self, key_name):
    with self.assertRaisesRegex(
        core.TinkError, r'key_name cannot be null|Invalid key_name format'
    ):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
          key_name, self.mock_client
      )

  def test_construction_unsupported_algorithm_fails(self):
    # SECP256K1 is deliberately unsupported: Tink has no secp256k1 verifier.
    self.mock_client.get_public_key.return_value = _public_key_response(
        algorithm=_Algorithm.EC_SIGN_SECP256K1_SHA256
    )
    with self.assertRaisesRegex(core.TinkError, r'is not supported'):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
          _KEY_VERSION_NAME, self.mock_client
      )

  def test_construction_get_public_key_rpc_fails(self):
    self.mock_client.get_public_key.side_effect = _MockGoogleApiError()
    with self.assertRaises(core.TinkError):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
          _KEY_VERSION_NAME, self.mock_client
      )

  def test_construction_malformed_pem_fails(self):
    self.mock_client.get_public_key.return_value = _public_key_response(
        algorithm=_Algorithm.EC_SIGN_P256_SHA256,
        data=b'-----BEGIN PUBLIC KEY-----\n'
        + base64.b64encode(b'not a valid spki')
        + b'\n-----END PUBLIC KEY-----',
    )
    with self.assertRaisesRegex(core.TinkError, r'Failed to parse'):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
          _KEY_VERSION_NAME, self.mock_client
      )

  def test_no_rpc_empty_fails(self):
    with self.assertRaisesRegex(core.TinkError, r'public_key cannot be empty'):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
          b'', _Algorithm.EC_SIGN_P256_SHA256
      )

  def test_no_rpc_unsupported_algorithm_fails(self):
    with self.assertRaisesRegex(core.TinkError, r'is not supported'):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
          _ECDSA_P256_PEM, _Algorithm.EC_SIGN_SECP256K1_SHA256
      )


if __name__ == '__main__':
  absltest.main()
