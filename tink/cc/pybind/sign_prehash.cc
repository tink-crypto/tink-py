// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
///////////////////////////////////////////////////////////////////////////////

#include "tink/cc/pybind/sign_prehash.h"

#include <memory>
#include <string>
#include <utility>

#include "absl/status/statusor.h"
#include "absl/strings/string_view.h"
#include "pybind11/pybind11.h"
#include "tink/insecure_secret_key_access.h"
#include "tink/keyset_handle.h"
#include "tink/proto_keyset_format.h"
#include "tink/signature/config_2026.h"
#include "tink/signature/sign_prehash.h"
#include "tink/cc/pybind/tink_exception.h"

namespace crypto {
namespace tink {

using pybind11::google_tink::TinkException;

namespace {

std::unique_ptr<SignPrehash> CreateSignPrehash(
    absl::string_view serialized_keyset) {
  absl::StatusOr<KeysetHandle> handle =
      ParseKeysetFromProtoKeysetFormat(serialized_keyset,
                                       InsecureSecretKeyAccess::Get());
  if (!handle.ok()) {
    throw TinkException(handle.status());
  }
  absl::StatusOr<std::unique_ptr<SignPrehash>> sign_prehash =
      handle->GetPrimitive<SignPrehash>(ConfigSignature2026());
  if (!sign_prehash.ok()) {
    throw TinkException(sign_prehash.status());
  }
  return *std::move(sign_prehash);
}

}  // namespace

void PybindRegisterSignPrehash(pybind11::module* module) {
  namespace py = pybind11;
  py::module& m = *module;

  py::class_<SignPrehash>(m, "SignPrehash", "Interface for prehash signing.")
      .def(
          "sign",
          [](const SignPrehash& self, const py::bytes& prehash) -> py::bytes {
            absl::StatusOr<std::string> result =
                self.Sign(std::string(prehash));
            if (!result.ok()) {
              throw TinkException(result.status());
            }
            return *std::move(result);
          },
          py::arg("prehash"), "Computes the signature for 'prehash'.");

  m.def("create_sign_prehash", &CreateSignPrehash, py::arg("keyset"),
        "Creates a SignPrehash primitive from a serialized keyset.");
}

}  // namespace tink
}  // namespace crypto
