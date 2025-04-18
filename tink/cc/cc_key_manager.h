// Copyright 2019 Google LLC
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

#ifndef TINK_PYTHON_TINK_CC_CC_KEY_MANAGER_H_
#define TINK_PYTHON_TINK_CC_CC_KEY_MANAGER_H_

#include <string>
#include <utility>

#include "absl/memory/memory.h"
#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"
#include "pybind11/pybind11.h"
#include "tink/key_manager.h"
#include "tink/registry.h"
#include "tink/cc/pybind/tink_exception.h"

namespace crypto {
namespace tink {

using pybind11::google_tink::TinkException;

/**
 * CcKeyManager is a thin wrapper of KeyManager in
 * third_party/tink/cc/key_manager.h
 * It only implements the methods currently needed in Python, and slightly
 * changes the interface to ease usage of pybind.
 */
template<class P>
class CcKeyManager {
 public:
  // Returns a key manager from the registry.
  static std::unique_ptr<CcKeyManager<P>> GetFromCcRegistry(
      const std::string& type_url) {
    auto key_manager_result = Registry::get_key_manager<P>(type_url);
    if (!key_manager_result.ok()) {
      throw TinkException(
          absl::Status(absl::StatusCode::kFailedPrecondition,
                       absl::StrCat("No manager for key type '", type_url,
                                    "' found in the registry.")));
    }
    return absl::make_unique<CcKeyManager<P>>(key_manager_result.value());
  }

  explicit CcKeyManager(const KeyManager<P>* key_manager)
      : key_manager_(key_manager) {}

  // Constructs an instance of P for the given 'key_data'.
  std::unique_ptr<P> GetPrimitive(
      const std::string& serialized_key_data) const {
    google::crypto::tink::KeyData key_data;
    key_data.ParseFromString(serialized_key_data);
    absl::StatusOr<std::unique_ptr<P>> result =
        key_manager_->GetPrimitive(key_data);
    if (!result.ok()) {
      throw TinkException(result.status());
    }
    return *std::move(result);
  }

  // Creates a new random key, based on the specified 'key_format'.
  pybind11::bytes NewKeyData(const std::string& serialized_key_template) const {
    google::crypto::tink::KeyTemplate key_template;
    key_template.ParseFromString(serialized_key_template);
    if (key_manager_->get_key_type() != key_template.type_url()) {
      throw TinkException(
          absl::Status(absl::StatusCode::kInvalidArgument,
                       absl::StrCat("Key type '", key_template.type_url(),
                                    "' is not supported by this manager.")));
    }

    auto key_data =
        key_manager_->get_key_factory().NewKeyData(key_template.value());
    if (!key_data.ok()) {
      throw TinkException(key_data.status());
    }
    return pybind11::bytes(key_data.value()->SerializeAsString());
  }

  // Returns public key data extracted from the given private_key_data.
  pybind11::bytes GetPublicKeyData(
      const std::string& serialized_private_key_data) const {
    const PrivateKeyFactory* factory = dynamic_cast<const PrivateKeyFactory*>(
        &key_manager_->get_key_factory());
    if (factory == nullptr) {
      throw TinkException(absl::Status(
          absl::StatusCode::kInvalidArgument,
          absl::StrCat("KeyManager for type '", key_manager_->get_key_type(),
                       "' does not have "
                       "a PrivateKeyFactory.")));
    }

    google::crypto::tink::KeyData private_key_data;
    private_key_data.ParseFromString(serialized_private_key_data);
    auto result = factory->GetPublicKeyData(private_key_data.value());
    if (!result.ok()) {
      throw TinkException(result.status());
    }
    return pybind11::bytes(result.value()->SerializeAsString());
  }

  // Returns the type_url identifying the key type handled by this manager.
  std::string KeyType() const { return key_manager_->get_key_type(); }

 private:
  const KeyManager<P>* key_manager_;
};

}  // namespace tink
}  // namespace crypto
#endif  // TINK_PYTHON_TINK_CC_CC_KEY_MANAGER_H_
