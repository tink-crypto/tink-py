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
from tink.integration.gcpkms import _gcp_kms_util

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

# Generated the private key with Cloud KMS and exported public key.
_ML_DSA_44_RAW_PUBLIC_KEY = base64.b64decode(
    '7fgDItYnOZpZOMclgf+Ex03S3MUIbgwUukjKnDL1q3Qbc+61vdsl4tcjhil+Pk8H3pQrwH0Z'
    'B8i+Mjg2jpxWnETbaoeotkwScgS0rp5avH2NibCHwEu5M9Q4Cvsj9dZorJnfInwJtbsX3m3Z'
    'KsZCpzf5hwkd08jfdbi0h660pxpDoGFtsH1i75J/46I1XI14/7K5C8x1JuaMo0ycPXOLaxV/'
    'WN7Vn0vixZETuntw+4QTZpKxcRLP31Msls4v8WPCwgOVyw60ZN3XzSJ4v1XH+aY1D+MYmMQT'
    'XE9eaHADAFe2O+l3WJy1l3QmKGAgUOqDdjnvj7RvULmeq/UxRFnU5EloRunwBj5bD7lbDRRa'
    'r+OmtHDRtYhscPFF26nKlnYL3TLwYRzrirD/MM7XonooYMCMhXymwcR41lWWJrGdBGRgS+0g'
    'XB6nMvL/maKtJG1X2pEiey5L0DmyEALB/ajTmnKlNEGMxCSfwmSZzC/p+WWBfgHxVpq8W5Cp'
    '/oMuWmhDYMNezv8d1H3MQaDBPvMiFJrshH/R5m7eKYgI6qFBVTdPxhGmeq33gLqahnil2dqu'
    'uyplVFGzgBHwv/Bpq6QH7ArLO6Hp+7WPr0LGcb2WDDmZc/fWXj/TXNa4uSLO5mr5u0boFmFC'
    '7ClZC3r3ACSqXFQtGzf4oBcUYXGb/cSihqIa6jbyYrwAgtDppjxBC78a9r/QIKkBUcY+WpYr'
    'JrAJxSXrMjju36rO76x0rY9yONAQqHkSXTqsptHXK+lFQ3UOOBF6MKjjvkPYy+HlCJcW6kpU'
    '/vXc0Psiwk312/z3hB7/y1yJV17R5EkkdeFyBylWyaJzwkkHIILtneLJ4d5VMnwM5xGETL0n'
    'Z2LAXkkD04mi6M5r1NlhZ7r7RV6etaA/r0QnjS01hiTErZ/cFrLE7tAxH9D0rTc0gLckCnu8'
    'yu85M7MAXa9MiGPzKVL9JJchYSvqriUHz6AKfaF/VU663Z39Lpy6DbemCAsgELrk/tuK2Grl'
    '+vbmCPqt6CwRFg/yqq7l0Ho3owHaXhP4h0ADNCqwOTXCidOd+9B9DZ5zdiUiXz4q+PuyjtWs'
    '0kvP34x1xi/IbzwULXJa8fA2mGxuMjN7kGvAvR17FUUbXU6O2wUv2sYIkqyXxKZis4XqbvXp'
    'D/b7JIVTTqaD0SG9IhnFxmh+MFcSqjjwsk84EJkF6byVa4wML/KMFCgr0ObeShEtjjQV+Kb5'
    'tct2Bo24HeDxiKKgqzy/eRzLV1JFumAQMJ0e7p/KBZzMZQ5Gdnb4fnFadCJOk6Jf/moq50Vr'
    '5o2+ZKiW608wBVSY1k1ZsEn3bmFkeM0JWF/Ge/sP3FK7ONjugdfL4SStTGu5vAllB5Ib9jj4'
    'yutm2vr6S/vG6spEINuyZ3Ad5uaNcKhG/4JV0FShTvhRD3ZeTvR/vwtCOjKVhVVv61h/cqiI'
    'OdNdPdlTSpNGGYhn69Iwfms2pha9kMiQ8XArFaAUtzJcVL0UUHfzhpJKNhuHfz9bLLLgFJrN'
    '8FoLOFXZKntgkm1ZKWXIpu37wNQ7T83FjKTF3zVjmZPcSrFaMdhx1JRmkVh0ymUo+glmtmPP'
    'aSwxdDWzZh2vjRUp45KUbHummlwNzvWUUOCf9rauW14xF+XAlFZXuAU2iyZDTqiXwU/+IKwc'
    'nkyw4Nt/vuV8KVJf3C4373rGkrD2xyouY2J/7SuLT84UfTagkRBEQpb6WLvJ0vUI1EyXV9C6'
    'YhjE3KlzvU+EfkPPEto++A=='
)
# Generated with Cloud KMS through AsymmetricSign for "data".
_ML_DSA_44_SIG = base64.b64decode(
    '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'
)
# Generated the private key with Cloud KMS and exported public key.
_ML_DSA_65_RAW_PUBLIC_KEY = base64.b64decode(
    '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'
    'ug4zT5/nX2w='
)
# Generated with Cloud KMS through AsymmetricSign for "data".
_ML_DSA_65_SIG = base64.b64decode(
    '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'
    'AAAAAAAAAAAACA0QGSAn'
)
# Generated the private key with Cloud KMS and exported public key.
_ML_DSA_87_RAW_PUBLIC_KEY = base64.b64decode(
    'Er+BPBEfywgH3VlZa21+/JHJzWxRr6JSJ0azghVoFtdxG5RM4XVSyl3f0vEX18WTTDAV0q6K'
    'cQDbnXLDtpeiE+o/3HPcmJJYVdqZB0diycSzijSx4H/f1o8H8AuZ8WxSwGlB5cX+3rWEhn7w'
    '0KcoukRr9F8qMktWkJsXe6Au8SLfx5YvwUHOV3weVUhbrsowVTjYGb0D31CSwoxqFYvzS1VM'
    'o0avMLO+LbMLUrbpL0S3hgrqT7DGmNOKmenjs82Qr4oyLToL3c2tS+v4y9/cA3tueTlIia43'
    '1DImcpgCpTIZdamMGNXUw0VnUQ5xMJ+WfMy4kMux5SI4GVg9zopWhnCsrntFI7MSd4YHGzx0'
    '0YGyeRywcgQhZzOVoupcJo2dQXtWFroMaGcGzJuijZ6YpYv0FboB83VK6Iss9a5QQIqU6Dy0'
    'yKZohD9J6nDKSEn5eED4HZfn46UtCjNt88G3So6VEpXgvsfRIE+SupEm4A8sClGc7klhBZqs'
    'wxZ7wkrp0uZewc68Kx2gNkFHKdTx+yAB1jiVLXnz83AHi3U5A4Z3CbdU1F08mo29tY4jLYoV'
    't8mKLdVMNuPqnwJh6I9x1bblt5eCldlP901masx1sMC52HVUkEBUC3WVwF2Srv2fv0CBc/zE'
    '1BfaGZhuz9EXgjyzTs+Wh5KFfs7qz53DBdyOk4CfuqaeR5ww38KELwoTUKcudwbMYrDDZQpW'
    'pS558+GKoyssatazYZhKdDXDDeFYPq/Ws5hSRYwSojq4HgcEo6duB8XjZrBtAzNUAZxELMP8'
    'zIZrKX8oTgcT/GmiBmBzZCKXe2wsIbRvxFiV+g4E27RITYL34O2VxXvWv+E1UG+XWRpZFI63'
    'V6BVJjffyFnI/j8TdBBlaqG0gj8hF/i19/ZUPZjBL/exQtvDWRLjNUii7I64YS4XTms1hwJT'
    'GHpjPap2KFTIj0oJmfDE5eKDBZ3+wyBCiMEUekQd8cQMvblKpewQMQXzdI+z7GMnkauJb3jz'
    'HAXHSbdkkBMSU6k1kdPgaoxjeh76rLuwdmvL1t0y1gvnhuIZDVzKU990FMG19C+b1fiUr0dp'
    'e/K4KPZXMyaQV9GafDG+/E83jm7WlckB1eFIJjptC7rkpq0ZbEkI/cWvfiTJB86GJbLDiAaw'
    '7ZTbjGJ1XfA7zALj+Ug4aZs5MGDe539YDD0lZ7M7dktNhc4VkPumllc/5BmiMHsO8N0Wnkab'
    'xDaOKwos8SrpYG0qHIRpnrHTzvWvsvnsuNaQRa0bGzFtJTRwCEVfoIpugRViswXGZEAA5/B/'
    'fQPUpgg6XLyuomkhD9Qf5rXo1KtCndBtTmhwm67Xi2FIuke5h53BzO+A5d/b6wJ4JNkqiFY1'
    'au73N7Jk+p7u94lAqCLXlQNERMz8tGkBjtrY4ib5fRZV9TBN7f2tIvwKzblmVXeGJVd/3kst'
    'mBTR9thZrjNP7ss5e504Qi1Y207OKp64BiZcgOU8Ic2vKMiCP9OJ4tEPcf7bgiUB6p0pq2um'
    'p+GddpfUQxf4CGGLfyoAU9fFhRFPUzYp1KzsiwJOon1xvalFTCnnqdakqAG7lvFBcYTwp/km'
    'wNfJgKyIl8BRKmqHdTeF4DI0FiDigTCufkt521P2eQeoCx0LKBWF72qPi1BB1/IO2bJTUkxc'
    'Duxe6QWExi4tyr9jchPTvVZQwkuYBYi1Frw+75YHjothy3xc+HjsuEYu4Fs2CCJBSD9ziTYD'
    'sNMo64EKKdSzeGnzGI0VJnehPYTeybPfrBdDUkaqqWGQ0z8YEDXd7KBgnnACj0TtyBU8tqmM'
    'QGOegxi4yg3S1fs9R5N4JlG1/ggH32lXVWxWQAlaqIjCdYELDgB0Y7LsBuCZtSvOo0Bqx5BN'
    'OhhqDwBoj4+IKxlaTY+tSC33D8Ot9vm4dgKoj8uLD22iiQObLTHKG232LOeOfW1xsLDhBaV7'
    'lidY93s0nPnTSjXZvqPYXN3Tux9m83EMLXwDbNZRfUWCSgWYEIUgweq8W+m0/ogbhNumCY1w'
    'mtdSKyqEkd2oFGBHZM0lED1JMZPLPaPa9ubzbvXZektSMljFMQ2oRyRqdMm3I+AVWASizZSm'
    'jlSBGyWb+e1b10tAJHebgh1AMdhmk9Is3Ye/e+qBS98OSxeeK/8jhkFcqkNyAu6UoNdyFpdV'
    'ICrU3pzoJkOJHpCYOcu9etpg1pZv/ZZ2DcDWuYDYCOCvsjrzKPi6YbMYQMbOnLqHk4snSqkj'
    'P46JTj2GVNqd/B5bMc/4eaQHxn/6kdEtEFKx6iVXFKtmZr+SJZPq0BvkecZmSbV87OeJIgr2'
    'EXCpWAkL6bKHVR2jvVFzGeKJVPk5fhfdjJ7d3oYyvZ5qu1MKmPeH9toOpl1IqhGZ0vr09Y4N'
    'lC/bYEHUU9lKExvnTNank2XWKoJoMn7QZf+NsVDM46UlWFNA7YRO8WKSGupm3pQ+V4SLpRcG'
    's84w2z8/rT/TmL9hjQme8WywhjpraBPgfP3lNfk/0ck0XDz1kViyxvh3io26qxCvZtMqHeCS'
    '9CaaHS71YydoVKyMdeAT8aEs8ZCH2GexOHZaFa6uLrm9qjgGZCyLn75KVQ8F8pZwDycEBdMM'
    'HZowgIhFIj3Pdra8vLOO4oIG3iIK+Pbs6fzTPDj7lF5++XQMaoxBr2ls8lorLrfMLgZlzcOC'
    '8oX2ERX4Izm+Agjy5wyFHM/r63XZufLg6mOgVrrX7zq+hqqBcseVq8BU2dMO1c2puL7PHH+V'
    'k04Bic3zzbo9lEv20KJqfRy3OUEZ4K0j5ewQ45f0h/scy5OtiZFBBQU1kOrT+frRkz7pRC/T'
    '8PEbhYX/fbZmb0ITClq6wFECpAYhg8c9CTslj6HgfLatMcnYpIw8tYVsUIfxWGY/3fFaj0r9'
    'SsE93YkLfAy2lkyNTQHnyZcR7dQ3w6uzTicvCuUlqWvcZgDQ6MEh9c2O8DTTnvipIKEXL6B/'
    'wJdJIyoZZix/7GysXQk/Atb1yZCF20LPtDGJx9X1/5iThgcnO9C4qlF6fyZb1OX+ZZDUz4Tb'
    'ao2ZlVKTUN7mry1cbIxlboN6/FP0zjJxC8sRAab12t/XMa3dXVIPDqvz3WGuF3Bu9seuqqbL'
    '5pat0pXPawxUWpq2As8S9+amiN8d+gx+rtxLn3EqnmeQsgAHvKBAbeW/UkerGiKkz4pBt3Qp'
    'jbLvEh8OE/dikTfP6+p14ImOR9HDnLSjUM9dB5vlKzBHWVqw941v6ovOS0LdkmTkNt/wDiaY'
    'i0bvIXUdS6MfEBmn6BTEoW5rGyRWpBHGa98/YEELIhzSeO8JFtVcR72L9XbL98rn19EgmIJ2'
    'e3Dvuks3DGyII0DLI2xyK2Vz20FHbxo9LqK/NySV6IPDFQs0ZGVOzSsVNQ8w2D/FQ3vc70fp'
    '3TdDqQ7Tg4fdufKBG6MXUVmrEAZNJkKn+ITXTBjEccBnPjjoXQutOE77DbF+muWyajLvgjRX'
)
# Generated with Cloud KMS through AsymmetricSign for "data".
_ML_DSA_87_SIG = base64.b64decode(
    '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'
)
# Generated the private key with Cloud KMS and exported public key.
_SLH_DSA_RAW_PUBLIC_KEY = base64.b64decode(
    'kdcOIrFCC5kN8S4i0+R+AoSc9gYIJ9jEQ6zG235ZmCQ='
)
# Generated with Cloud KMS through AsymmetricSign for "data".
_SLH_DSA_SIG = base64.b64decode(
    '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'
    'h/ZT9ktaAEtsgTO1JNDuWrxYmQakV5zQqg0='
)


def _ml_dsa_pem(algorithm: _Algorithm, raw_public_key: bytes) -> bytes:
  """Wraps a raw ML-DSA public key in the PEM that Cloud KMS would return."""
  _, oid, _ = _gcp_kms_public_key_verify._ML_DSA_PARAMS[algorithm]
  return _gcp_kms_util.raw_ml_dsa_public_key_to_pem(oid, raw_public_key)


# Algorithms that Cloud KMS serves as a single PEM GetPublicKey response,
# mapped to (public key PEM, signature). This covers all the classical
# algorithms and ML-DSA.
_PEM_TEST_VECTORS = {
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
    _Algorithm.PQ_SIGN_ML_DSA_44: (
        _ml_dsa_pem(_Algorithm.PQ_SIGN_ML_DSA_44, _ML_DSA_44_RAW_PUBLIC_KEY),
        _ML_DSA_44_SIG,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_65: (
        _ml_dsa_pem(_Algorithm.PQ_SIGN_ML_DSA_65, _ML_DSA_65_RAW_PUBLIC_KEY),
        _ML_DSA_65_SIG,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_87: (
        _ml_dsa_pem(_Algorithm.PQ_SIGN_ML_DSA_87, _ML_DSA_87_RAW_PUBLIC_KEY),
        _ML_DSA_87_SIG,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_44_EXTERNAL_MU: (
        _ml_dsa_pem(
            _Algorithm.PQ_SIGN_ML_DSA_44_EXTERNAL_MU, _ML_DSA_44_RAW_PUBLIC_KEY
        ),
        _ML_DSA_44_SIG,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_65_EXTERNAL_MU: (
        _ml_dsa_pem(
            _Algorithm.PQ_SIGN_ML_DSA_65_EXTERNAL_MU, _ML_DSA_65_RAW_PUBLIC_KEY
        ),
        _ML_DSA_65_SIG,
    ),
    _Algorithm.PQ_SIGN_ML_DSA_87_EXTERNAL_MU: (
        _ml_dsa_pem(
            _Algorithm.PQ_SIGN_ML_DSA_87_EXTERNAL_MU, _ML_DSA_87_RAW_PUBLIC_KEY
        ),
        _ML_DSA_87_SIG,
    ),
}

# Every supported algorithm mapped to (public key material, signature), where
# the material is exactly what GetPublicKey returns: a PEM for the classical and
# ML-DSA keys, and the raw NIST_PQC key for SLH-DSA. Used by the offline
# (no-RPC) tests, which take the material directly.
_ALL_TEST_VECTORS = {
    **_PEM_TEST_VECTORS,
    _Algorithm.PQ_SIGN_SLH_DSA_SHA2_128S: (
        _SLH_DSA_RAW_PUBLIC_KEY,
        _SLH_DSA_SIG,
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

  @parameterized.parameters(*_PEM_TEST_VECTORS.items())
  def test_verify_pem_succeeds(self, algorithm, vector):
    pem, sig = vector
    self.mock_client.get_public_key.return_value = _public_key_response(
        algorithm=algorithm, data=pem
    )
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
        _KEY_VERSION_NAME, self.mock_client
    )
    self.assertIsNone(verifier.verify(sig, _MESSAGE))

  def test_verify_slh_dsa_succeeds(self):
    # Cloud KMS does not serve SLH-DSA in PEM format, so GetPublicKey is called
    # twice: the PEM request fails and the raw key is fetched with NIST_PQC.
    self.mock_client.get_public_key.side_effect = [
        _MockGoogleApiError('Only NIST_PQC format is supported'),
        _public_key_response(
            algorithm=_Algorithm.PQ_SIGN_SLH_DSA_SHA2_128S,
            data=_SLH_DSA_RAW_PUBLIC_KEY,
        ),
    ]
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
        _KEY_VERSION_NAME, self.mock_client
    )
    self.assertIsNone(verifier.verify(_SLH_DSA_SIG, _MESSAGE))
    self.assertEqual(self.mock_client.get_public_key.call_count, 2)

  @parameterized.parameters(
      _Algorithm.PQ_SIGN_ML_DSA_65,
      _Algorithm.PQ_SIGN_ML_DSA_65_EXTERNAL_MU,
  )
  def test_verify_ml_dsa_fetches_pem_only(self, algorithm):
    # ML-DSA (including external-mu) is served as PEM and parsed locally, so
    # unlike SLH-DSA it needs a single GetPublicKey call with no NIST_PQC
    # re-fetch.
    pem, _ = _PEM_TEST_VECTORS[algorithm]
    self.mock_client.get_public_key.return_value = _public_key_response(
        algorithm=algorithm, data=pem
    )
    _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify(
        _KEY_VERSION_NAME, self.mock_client
    )
    self.mock_client.get_public_key.assert_called_once()
    request = self.mock_client.get_public_key.call_args.kwargs['request']
    self.assertEqual(
        request.public_key_format, kms_v1.PublicKey.PublicKeyFormat.PEM
    )

  @parameterized.parameters(*_ALL_TEST_VECTORS.items())
  def test_verify_no_rpc_succeeds(self, algorithm, vector):
    public_key, sig = vector
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
        public_key, algorithm
    )
    self.assertIsNone(verifier.verify(sig, _MESSAGE))

  @parameterized.parameters(*_ALL_TEST_VECTORS.items())
  def test_verify_wrong_data_fails(self, algorithm, vector):
    public_key, sig = vector
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
        public_key, algorithm
    )
    with self.assertRaises(core.TinkError):
      verifier.verify(sig, b'wrong data')

  @parameterized.parameters(*_ALL_TEST_VECTORS.items())
  def test_verify_wrong_signature_fails(self, algorithm, vector):
    public_key, sig = vector
    verifier = _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
        public_key, algorithm
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

  def test_no_rpc_ml_dsa_wrong_size_fails(self):
    algorithm = _Algorithm.PQ_SIGN_ML_DSA_65
    _, _, size = _gcp_kms_public_key_verify._ML_DSA_PARAMS[algorithm]
    pem = _ml_dsa_pem(algorithm, bytes(size - 1))
    with self.assertRaisesRegex(core.TinkError, r'Incorrect public key size'):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
          pem, algorithm
      )

  def test_no_rpc_ml_dsa_wrong_oid_fails(self):
    algorithm = _Algorithm.PQ_SIGN_ML_DSA_65
    _, _, size = _gcp_kms_public_key_verify._ML_DSA_PARAMS[algorithm]
    pem = _gcp_kms_util.raw_ml_dsa_public_key_to_pem('1.2.3.4', bytes(size))
    with self.assertRaisesRegex(core.TinkError, r'Unexpected public key OID'):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
          pem, algorithm
      )

  def test_no_rpc_slh_dsa_wrong_size_fails(self):
    with self.assertRaises(core.TinkError):
      _gcp_kms_public_key_verify.new_gcp_kms_public_key_verify_no_rpc(
          _SLH_DSA_RAW_PUBLIC_KEY[:-1], _Algorithm.PQ_SIGN_SLH_DSA_SHA2_128S
      )


if __name__ == '__main__':
  absltest.main()
