#!/usr/bin/env python3
"""校验父仓库版本化 contracts 权威目录。"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable


MANIFEST_FORMAT = "testplat.contracts-manifest"
MATRIX_FORMAT = "testplat.compatibility-matrix"
FORMAT_VERSION = "1.0"
VERSION_RE = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
ID_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
FEATURE_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUIRED_DIRS = ("schemas", "fixtures", "errors", "compatibility")
MAX_SAFE_INTEGER = (2**53) - 1
AUXILIARY_REGISTRIES = (
    ("schemas/manifest.json", "testplat.schema-manifest", "schemas"),
    ("fixtures/manifest.json", "testplat.fixture-manifest", "fixtures"),
    ("errors/registry.json", "testplat.error-registry", "codes"),
)


class ValidationFailure(Exception):
    """稳定、可供 CI 消费的用户侧校验失败。"""

    def __init__(self, code: str, location: str, message: str) -> None:
        self.code = code
        self.location = location
        self.message = message
        super().__init__(f"{code}: {location}: {message}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationFailure("DUPLICATE_KEY", "json", f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise ValidationFailure("INVALID_JSON_NUMBER", "json", f"non-I-JSON number {value!r} is not allowed")


def parse_json_document(text: str, location: str) -> Any:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except ValidationFailure:
        raise
    except json.JSONDecodeError as exc:
        raise ValidationFailure("INVALID_JSON", location, str(exc)) from exc
    validate_ijson(value, location)
    return value


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return parse_json_document(handle.read(), str(path))
    except ValidationFailure:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure("INVALID_JSON", str(path), str(exc)) from exc


def _json_string(value: str) -> str:
    return json.dumps(_unicode_scalars(value), ensure_ascii=False, separators=(",", ":"))


def _unicode_scalars(value: str, location: str = "payload") -> str:
    """将合法 UTF-16 surrogate pair 合并为 Unicode 标量，拒绝孤立 surrogate。"""
    if not isinstance(value, str):
        raise ValidationFailure("INVALID_UNICODE", location, "JSON strings must be Unicode text")
    scalars: list[str] = []
    index = 0
    while index < len(value):
        codepoint = ord(value[index])
        if 0xD800 <= codepoint <= 0xDBFF:
            if index + 1 >= len(value) or not 0xDC00 <= ord(value[index + 1]) <= 0xDFFF:
                raise ValidationFailure("INVALID_UNICODE", location, "lone UTF-16 surrogate is not valid I-JSON")
            pair = 0x10000 + ((codepoint - 0xD800) << 10) + (ord(value[index + 1]) - 0xDC00)
            scalars.append(chr(pair))
            index += 2
            continue
        if 0xDC00 <= codepoint <= 0xDFFF:
            raise ValidationFailure("INVALID_UNICODE", location, "lone UTF-16 surrogate is not valid I-JSON")
        scalars.append(value[index])
        index += 1
    return "".join(scalars)


def validate_ijson(value: Any, location: str) -> None:
    """递归检查所有元数据，避免未参与摘要的值绕过 I-JSON 边界。"""
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise ValidationFailure("UNSAFE_INTEGER", location, "JSON integers exceed the I-JSON safe range")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationFailure("INVALID_JSON_NUMBER", location, "NaN and Infinity are not valid I-JSON values")
        return
    if isinstance(value, str):
        _unicode_scalars(value, location)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_ijson(item, f"{location}[{index}]")
        return
    if isinstance(value, dict):
        normalized_keys: set[str] = set()
        for key, item in value.items():
            normalized_key = _unicode_scalars(key, f"{location}.<key>")
            if normalized_key in normalized_keys:
                raise ValidationFailure("DUPLICATE_KEY", location, f"duplicate Unicode key {key!r}")
            normalized_keys.add(normalized_key)
            validate_ijson(item, f"{location}.{normalized_key}")
        return
    raise ValidationFailure("INVALID_JSON_VALUE", location, f"unsupported value {type(value).__name__}")


def _number(value: int | float) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise ValidationFailure(
                "UNSAFE_INTEGER",
                "payload",
                f"JSON integers must be within [-{MAX_SAFE_INTEGER}, {MAX_SAFE_INTEGER}] for I-JSON",
            )
        return str(value)
    if not math.isfinite(value):
        raise ValidationFailure("INVALID_JSON_NUMBER", "payload", "NaN and Infinity are not valid JCS values")
    if value == 0:
        return "0"

    # Python 的 repr 已是最短往返表示；这里再按 RFC 8785 的 ECMAScript
    # 阈值归一化指数/定点形式，避免不同工具对同一 JSON 产生不同摘要。
    text = repr(value).lower()
    coefficient, separator, exponent_text = text.partition("e")
    exponent = int(exponent_text) if separator else 0
    if coefficient.endswith(".0"):
        coefficient = coefficient[:-2]
    if not separator:
        return coefficient
    digits = coefficient.replace(".", "").replace("-", "")
    sign = "-" if coefficient.startswith("-") else ""
    unsigned_coefficient = coefficient[1:] if coefficient.startswith("-") else coefficient
    decimal_position = (unsigned_coefficient.find(".") if "." in unsigned_coefficient else len(unsigned_coefficient)) + exponent
    # JCS 在 1e-6（含）到 1e21（不含）之间使用定点形式，其余使用指数形式。
    if -6 < decimal_position <= 21:
        if decimal_position <= 0:
            return f"{sign}0.{('0' * -decimal_position)}{digits}"
        if decimal_position >= len(digits):
            return f"{sign}{digits}{'0' * (decimal_position - len(digits))}"
        return f"{sign}{digits[:decimal_position]}.{digits[decimal_position:]}"
    exponent_sign = "+" if exponent >= 0 else "-"
    return f"{sign}{digits[0]}{('.' + digits[1:]) if len(digits) > 1 else ''}e{exponent_sign}{abs(exponent)}"


def jcs(value: Any) -> str:
    """按 RFC 8785 排序并生成紧凑 JSON，作为摘要输入。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _number(value)
    if isinstance(value, str):
        return _json_string(value)
    if isinstance(value, list):
        return "[" + ",".join(jcs(item) for item in value) + "]"
    if isinstance(value, dict):
        # RFC 8785 按 UTF-16 code unit 排序，而不是按本地化或 Python code point 排序。
        normalized_keys: dict[str, str] = {}
        for key in value:
            if not isinstance(key, str):
                raise ValidationFailure("INVALID_JSON_VALUE", "payload", "JSON object keys must be strings")
            normalized_keys[key] = _unicode_scalars(key)
        if len(set(normalized_keys.values())) != len(normalized_keys):
            raise ValidationFailure("DUPLICATE_KEY", "payload", "JSON object keys must be unique Unicode scalars")
        keys = sorted(value, key=lambda key: normalized_keys[key].encode("utf-16-be"))
        return "{" + ",".join(f"{_json_string(key)}:{jcs(value[key])}" for key in keys) + "}"
    raise ValidationFailure("INVALID_JSON_VALUE", "payload", f"unsupported value {type(value).__name__}")


def digest_payload(path: Path) -> str:
    try:
        raw = path.read_bytes()
        if path.suffix.lower() == ".json":
            content = jcs(parse_json_document(raw.decode("utf-8"), str(path))).encode("utf-8")
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw
            else:
                try:
                    content = jcs(parse_json_document(text, str(path))).encode("utf-8")
                except ValidationFailure as exc:
                    # 非 .json 文件只有在确实不是 JSON 时才按原始字节摘要；
                    # 一旦识别为 JSON 但违反 I-JSON，必须拒绝而不能降级绕过规则。
                    if exc.code == "INVALID_JSON":
                        content = raw
                    else:
                        raise
    except ValidationFailure:
        raise
    except UnicodeError as exc:
        raise ValidationFailure("INVALID_UNICODE", str(path), "payload contains invalid Unicode") from exc
    except OSError as exc:
        raise ValidationFailure("UNREADABLE_PAYLOAD", str(path), str(exc)) from exc
    return "sha256:" + hashlib.sha256(content).hexdigest()


def require_object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationFailure("INVALID_OBJECT", location, "expected a JSON object")
    return value


def require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationFailure("INVALID_STRING", location, "expected a non-empty string")
    return _unicode_scalars(value, location)


def require_version(value: Any, location: str) -> str:
    version = require_string(value, location)
    if not VERSION_RE.fullmatch(version):
        raise ValidationFailure("INVALID_VERSION", location, "expected canonical major.minor integers")
    return version


def require_format_version(value: Any, location: str) -> str:
    version = require_version(value, location)
    if version != FORMAT_VERSION:
        raise ValidationFailure("INVALID_VERSION", location, f"only format version {FORMAT_VERSION} is supported")
    return version


def require_features(value: Any, location: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationFailure("INVALID_FEATURES", location, "expected an array of feature IDs")
    if len(set(value)) != len(value):
        raise ValidationFailure("DUPLICATE_FEATURE", location, "feature IDs must be unique")
    for item in value:
        if not FEATURE_RE.fullmatch(item):
            raise ValidationFailure("INVALID_FEATURE", location, f"invalid feature ID {item!r}")
    return value


def resolve_inside(root: Path, candidate: Path, location: str) -> Path:
    """统一解析并限制路径，防止 target、注册表或目录符号链接逃出 contracts。"""
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValidationFailure("PATH_ESCAPE", location, "path must remain inside contracts/")
    try:
        resolved_root = root.resolve()
        resolved_candidate = (resolved_root / candidate).resolve()
        resolved_candidate.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValidationFailure("PATH_ESCAPE", location, "resolved path is outside contracts/") from exc
    return resolved_candidate


def safe_payload_path(root: Path, raw: Any, location: str) -> Path:
    relative = require_string(raw, location)
    path = resolve_inside(root, Path(relative), location)
    if not path.is_file():
        raise ValidationFailure("MISSING_PAYLOAD", location, f"payload not found: {relative}")
    return path


def load_root(root: Path, target: str | None = None) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    try:
        root = Path(root).resolve()
    except (OSError, RuntimeError) as exc:
        raise ValidationFailure("PATH_ESCAPE", str(root), "contracts root cannot be resolved") from exc
    if not root.is_dir():
        raise ValidationFailure("EMPTY_DIRECTORY", str(root), "contracts root does not exist or is not a directory")
    if target is not None:
        target_path = resolve_inside(root, Path(target), "target")
        if not target_path.is_dir() or not any(target_path.iterdir()):
            raise ValidationFailure("EMPTY_DIRECTORY", str(target_path), "target directory is missing or empty")
    for directory in REQUIRED_DIRS:
        path = resolve_inside(root, Path(directory), f"contracts/{directory}")
        if not path.is_dir() or not any(path.iterdir()):
            raise ValidationFailure("EMPTY_DIRECTORY", str(path), "required contracts directory is missing or empty")
    manifest_path = resolve_inside(root, Path("manifest.json"), "manifest.json")
    matrix_path = resolve_inside(root, Path("compatibility/matrix.json"), "compatibility/matrix.json")
    if not manifest_path.is_file():
        raise ValidationFailure("MISSING_FILE", str(manifest_path), "manifest is required")
    if not matrix_path.is_file():
        raise ValidationFailure("MISSING_FILE", str(matrix_path), "compatibility matrix is required")
    return root, require_object(read_json(manifest_path), str(manifest_path)), require_object(read_json(matrix_path), str(matrix_path))


def validate_auxiliary_registries(root: Path, seen_ids: set[str]) -> None:
    for relative, expected_format, entries_key in AUXILIARY_REGISTRIES:
        path = resolve_inside(root, Path(relative), relative)
        if not path.is_file():
            raise ValidationFailure("MISSING_FILE", str(path), "contracts registry is required")
        registry = require_object(read_json(path), str(path))
        if registry.get("format") != expected_format:
            raise ValidationFailure("INVALID_FORMAT", f"{relative}.format", f"expected {expected_format!r}")
        require_format_version(registry.get("formatVersion"), f"{relative}.formatVersion")
        entries = registry.get(entries_key)
        if not isinstance(entries, list):
            raise ValidationFailure("INVALID_REGISTRY", f"{relative}.{entries_key}", "expected an array")
        validate_registry_entries(root, relative, entries, entries_key, seen_ids)


def validate_registry_entries(root: Path, registry: str, entries: list[Any], entries_key: str, seen_ids: set[str]) -> None:
    for index, raw in enumerate(entries):
        location = f"{registry}.{entries_key}[{index}]"
        entry = require_object(raw, location)
        entry_id = require_string(entry.get("id"), f"{location}.id")
        if not ID_RE.fullmatch(entry_id):
            raise ValidationFailure("INVALID_ID", f"{location}.id", "must contain lowercase stable identifier characters")
        register_id(entry_id, f"{location}.id", seen_ids)
        require_version(entry.get("version"), f"{location}.version")
        payload = safe_payload_path(root, entry.get("payload"), f"{location}.payload")
        digest = require_string(entry.get("sha256"), f"{location}.sha256")
        if not SHA256_RE.fullmatch(digest):
            raise ValidationFailure("INVALID_DIGEST", f"{location}.sha256", "expected sha256:<64 lowercase hex>")
        actual = digest_payload(payload)
        if digest != actual:
            raise ValidationFailure("DIGEST_MISMATCH", f"{location}.sha256", f"expected {actual}, got {digest}")


def register_id(identifier: str, location: str, seen_ids: set[str]) -> None:
    if identifier in seen_ids:
        raise ValidationFailure("DUPLICATE_ID", location, f"duplicate global ID {identifier!r}")
    seen_ids.add(identifier)


def validate_manifest(root: Path, manifest: dict[str, Any], seen_ids: set[str]) -> list[dict[str, Any]]:
    if manifest.get("format") != MANIFEST_FORMAT:
        raise ValidationFailure("INVALID_FORMAT", "manifest.format", f"expected {MANIFEST_FORMAT!r}")
    require_format_version(manifest.get("formatVersion"), "manifest.formatVersion")
    contracts = manifest.get("contracts")
    if not isinstance(contracts, list):
        raise ValidationFailure("INVALID_CONTRACTS", "manifest.contracts", "expected an array")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(contracts):
        location = f"manifest.contracts[{index}]"
        entry = require_object(raw, location)
        contract_id = require_string(entry.get("id"), f"{location}.id")
        if not ID_RE.fullmatch(contract_id):
            raise ValidationFailure("INVALID_ID", f"{location}.id", "must contain lowercase stable identifier characters")
        register_id(contract_id, f"{location}.id", seen_ids)
        version = require_version(entry.get("version"), f"{location}.version")
        family = require_string(entry.get("family"), f"{location}.family")
        payload = safe_payload_path(root, entry.get("payload"), f"{location}.payload")
        digest = require_string(entry.get("sha256"), f"{location}.sha256")
        if not SHA256_RE.fullmatch(digest):
            raise ValidationFailure("INVALID_DIGEST", f"{location}.sha256", "expected sha256:<64 lowercase hex>")
        actual = digest_payload(payload)
        if digest != actual:
            raise ValidationFailure("DIGEST_MISMATCH", f"{location}.sha256", f"expected {actual}, got {digest}")
        required = require_features(entry.get("requiredFeatures"), f"{location}.requiredFeatures")
        optional = require_features(entry.get("optionalFeatures"), f"{location}.optionalFeatures")
        if set(required) & set(optional):
            raise ValidationFailure("FEATURE_OVERLAP", location, "a feature cannot be both required and optional")
        normalized.append({"id": contract_id, "version": version, "family": family, "requiredFeatures": required, "optionalFeatures": optional})
    return normalized


def validate_matrix(matrix: dict[str, Any], seen_ids: set[str]) -> dict[str, dict[str, Any]]:
    if matrix.get("format") != MATRIX_FORMAT:
        raise ValidationFailure("INVALID_FORMAT", "compatibility.matrix.format", f"expected {MATRIX_FORMAT!r}")
    require_format_version(matrix.get("formatVersion"), "compatibility.matrix.formatVersion")
    families = matrix.get("families")
    if not isinstance(families, list):
        raise ValidationFailure("INVALID_FAMILIES", "compatibility.matrix.families", "expected an array")
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(families):
        location = f"compatibility.matrix.families[{index}]"
        family = require_object(raw, location)
        family_id = require_string(family.get("id"), f"{location}.id")
        if not ID_RE.fullmatch(family_id):
            raise ValidationFailure("INVALID_ID", f"{location}.id", "must contain lowercase stable identifier characters")
        register_id(family_id, f"{location}.id", seen_ids)
        versions = family.get("supportedVersions")
        if not isinstance(versions, list) or not versions:
            raise ValidationFailure("INVALID_VERSIONS", f"{location}.supportedVersions", "expected a non-empty array")
        for version in versions:
            require_version(version, f"{location}.supportedVersions")
        if len(set(versions)) != len(versions):
            raise ValidationFailure("DUPLICATE_VERSION", f"{location}.supportedVersions", "versions must be unique")
        features = require_features(family.get("knownFeatures"), f"{location}.knownFeatures")
        result[family_id] = {"versions": set(versions), "features": set(features)}
    return result


def check(root: Path, target: str | None) -> None:
    root, manifest, matrix = load_root(root, target)
    seen_ids: set[str] = set()
    validate_manifest(root, manifest, seen_ids)
    validate_auxiliary_registries(root, seen_ids)
    validate_matrix(matrix, seen_ids)


def compat(root: Path, target: str | None) -> None:
    root, manifest, matrix = load_root(root, target)
    seen_ids: set[str] = set()
    entries = validate_manifest(root, manifest, seen_ids)
    validate_auxiliary_registries(root, seen_ids)
    families = validate_matrix(matrix, seen_ids)
    for entry in entries:
        location = f"manifest.contracts[{entry['id']}]"
        family = families.get(entry["family"])
        if family is None:
            raise ValidationFailure("UNKNOWN_FAMILY", f"{location}.family", f"family {entry['family']!r} is not in compatibility matrix")
        if entry["version"] not in family["versions"]:
            raise ValidationFailure("INCOMPATIBLE_VERSION", f"{location}.version", f"{entry['version']} is not supported for {entry['family']}")
        unknown = sorted(set(entry["requiredFeatures"]) - family["features"])
        if unknown:
            raise ValidationFailure("UNKNOWN_REQUIRED_FEATURE", f"{location}.requiredFeatures", ", ".join(unknown))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the contracts authority")
    parser.add_argument("command", choices=("check", "compat"))
    parser.add_argument("--root", type=Path, default=Path("contracts"))
    parser.add_argument("--target", help="validate a non-empty target subdirectory")
    args = parser.parse_args(argv)
    try:
        # Makefile 对空 TARGET 仍传入空字符串；统一视为未指定 target。
        if args.target == "":
            args.target = None
        if args.command == "check":
            check(args.root, args.target)
            print("contracts-check: ok")
        else:
            compat(args.root, args.target)
            print("contracts-compat: ok")
    except ValidationFailure as exc:
        print(f"ERROR {exc.code}: {exc.location}: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
