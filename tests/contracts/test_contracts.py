from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "contracts.py"


class ContractsAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "contracts"
        for directory in ("schemas", "fixtures", "errors", "compatibility"):
            (self.root / directory).mkdir(parents=True)
            (self.root / directory / "README.md").write_text("fixture\n", encoding="utf-8")
        (self.root / "manifest.json").write_text(
            json.dumps({"format": "testplat.contracts-manifest", "formatVersion": "1.0", "contracts": []}),
            encoding="utf-8",
        )
        (self.root / "compatibility" / "matrix.json").write_text(
            json.dumps({"format": "testplat.compatibility-matrix", "formatVersion": "1.0", "families": []}),
            encoding="utf-8",
        )
        (self.root / "schemas" / "manifest.json").write_text(
            json.dumps({"format": "testplat.schema-manifest", "formatVersion": "1.0", "schemas": []}),
            encoding="utf-8",
        )
        (self.root / "fixtures" / "manifest.json").write_text(
            json.dumps({"format": "testplat.fixture-manifest", "formatVersion": "1.0", "fixtures": []}),
            encoding="utf-8",
        )
        (self.root / "errors" / "registry.json").write_text(
            json.dumps({"format": "testplat.error-registry", "formatVersion": "1.0", "codes": []}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_tool(self, command: str, target: str | None = None) -> subprocess.CompletedProcess[str]:
        args = ["python3", str(TOOL), command, "--root", str(self.root)]
        if target is not None:
            args.extend(["--target", target])
        return subprocess.run(
            args,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_failure(self, result: subprocess.CompletedProcess[str], code: str) -> None:
        # 保留 stderr 作为失败诊断，避免边界回归只报告一个无上下文的断言失败。
        self.assertNotEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(code, result.stderr, msg=result.stderr)
        self.assertNotIn("Traceback", result.stderr, msg=result.stderr)

    def load_tool(self):
        from importlib.util import module_from_spec, spec_from_file_location

        spec = spec_from_file_location("contracts_tool", TOOL)
        assert spec and spec.loader
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def write_contract(self, *, version: str = "1.0", required: list[str] | None = None, duplicate: bool = False) -> None:
        payload = self.root / "payload.json"
        payload.write_text('{"name":"self-test","value":1}\n', encoding="utf-8")
        digest = self.load_tool().digest_payload(payload)
        entry = {
            "id": "foundation.self-test",
            "family": "foundation",
            "version": version,
            "payload": "payload.json",
            "sha256": digest,
            "requiredFeatures": required or [],
            "optionalFeatures": [],
        }
        entries = [entry, dict(entry)] if duplicate else [entry]
        (self.root / "manifest.json").write_text(
            json.dumps({"format": "testplat.contracts-manifest", "formatVersion": "1.0", "contracts": entries}),
            encoding="utf-8",
        )
        (self.root / "compatibility" / "matrix.json").write_text(
            json.dumps(
                {
                    "format": "testplat.compatibility-matrix",
                    "formatVersion": "1.0",
                    "families": [{"id": "foundation", "supportedVersions": ["1.0"], "knownFeatures": []}],
                }
            ),
            encoding="utf-8",
        )

    def test_repository_commands_pass(self) -> None:
        self.assertEqual(subprocess.run(["make", "contracts-check"], cwd=ROOT, capture_output=True, text=True).returncode, 0)
        self.assertEqual(subprocess.run(["make", "contracts-compat"], cwd=ROOT, capture_output=True, text=True).returncode, 0)

    def test_empty_directory_is_rejected(self) -> None:
        shutil.rmtree(self.root / "schemas")
        result = self.run_tool("check")
        self.assert_failure(result, "EMPTY_DIRECTORY")

    def test_duplicate_id_is_rejected(self) -> None:
        self.write_contract(duplicate=True)
        result = self.run_tool("check")
        self.assert_failure(result, "DUPLICATE_ID")

    def test_illegal_version_is_rejected(self) -> None:
        self.write_contract(version="1.0.0")
        result = self.run_tool("check")
        self.assert_failure(result, "INVALID_VERSION")

    def test_digest_mismatch_is_rejected(self) -> None:
        self.write_contract()
        payload = self.root / "payload.json"
        payload.write_text('{"name":"tampered","value":1}\n', encoding="utf-8")
        result = self.run_tool("check")
        self.assert_failure(result, "DIGEST_MISMATCH")

    def test_unknown_required_feature_is_rejected(self) -> None:
        self.write_contract(required=["future.required.feature"])
        result = self.run_tool("compat")
        self.assert_failure(result, "UNKNOWN_REQUIRED_FEATURE")

    def test_duplicate_id_across_manifest_and_registry_is_rejected(self) -> None:
        self.write_contract()
        self.write_registry_entry("schemas/manifest.json", "schemas")
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["contracts"][0]["id"] = "foundation.registry-entry"
        (self.root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assert_failure(self.run_tool("check"), "DUPLICATE_ID")

    def test_metadata_rejects_non_i_json_numbers_and_surrogates(self) -> None:
        (self.root / "manifest.json").write_text(
            '{"format":"testplat.contracts-manifest","formatVersion":"1.0","unused":NaN,"contracts":[]}\n',
            encoding="utf-8",
        )
        self.assert_failure(self.run_tool("check"), "INVALID_JSON_NUMBER")
        (self.root / "manifest.json").write_text(
            '{"format":"testplat.contracts-manifest","formatVersion":"1.0","unused":"\\ud800","contracts":[]}\n',
            encoding="utf-8",
        )
        self.assert_failure(self.run_tool("check"), "INVALID_UNICODE")

    def test_jcs_number_boundaries_are_stable(self) -> None:
        module = self.load_tool()
        self.assertEqual(module.jcs(0.000001), "0.000001")
        self.assertEqual(module.jcs(0.0000001), "1e-7")
        self.assertEqual(module.jcs(-0.0000012), "-0.0000012")
        self.assertEqual(module.jcs(1e20), "100000000000000000000")
        self.assertEqual(module.jcs(1e21), "1e+21")

    def test_jcs_matches_rfc8785_appendix_b_number_vectors(self) -> None:
        # RFC 8785 Appendix B: https://www.rfc-editor.org/rfc/rfc8785#appendix-B
        module = self.load_tool()
        vectors = (
            (5e-324, "5e-324"),
            (-5e-324, "-5e-324"),
            (1.7976931348623157e308, "1.7976931348623157e+308"),
            (-1.7976931348623157e308, "-1.7976931348623157e+308"),
            (float(9007199254740992), "9007199254740992"),
            (float(295147905179352830000), "295147905179352830000"),
            (9.999999999999997e22, "9.999999999999997e+22"),
            (1e23, "1e+23"),
            (1.0000000000000001e23, "1.0000000000000001e+23"),
            (float(999999999999999700000), "999999999999999700000"),
            (float(999999999999999900000), "999999999999999900000"),
            (1e21, "1e+21"),
            (9.999999999999997e-7, "9.999999999999997e-7"),
            (1e-6, "0.000001"),
            (333333333.3333332, "333333333.3333332"),
            (333333333.33333325, "333333333.33333325"),
            (333333333.3333333, "333333333.3333333"),
            (333333333.3333334, "333333333.3333334"),
            (333333333.33333343, "333333333.33333343"),
            (-3.3333333333333333e-6, "-0.0000033333333333333333"),
            (1424953923781206.2, "1424953923781206.2"),
        )
        for value, expected in vectors:
            with self.subTest(value=value):
                self.assertEqual(module.jcs(value), expected)

    def test_json_payload_is_canonicalized_without_json_suffix(self) -> None:
        module = self.load_tool()
        payload = self.root / "payload.data"
        payload.write_text('{"b":2,"a":1}\n', encoding="utf-8")
        expected = "sha256:" + hashlib.sha256(module.jcs({"a": 1, "b": 2}).encode("utf-8")).hexdigest()
        self.assertEqual(module.digest_payload(payload), expected)

    def test_jcs_rejects_integers_outside_i_json_safe_range(self) -> None:
        module = self.load_tool()
        self.assertEqual(module.jcs(2**53 - 1), str(2**53 - 1))
        self.assertEqual(module.jcs(-(2**53 - 1)), str(-(2**53 - 1)))
        for value in (2**53, -(2**53)):
            with self.assertRaises(module.ValidationFailure) as context:
                module.jcs(value)
            self.assertEqual(context.exception.code, "UNSAFE_INTEGER")

        payload = self.root / "unsafe-integer.json"
        payload.write_text('{"value":9007199254740992}\n', encoding="utf-8")
        (self.root / "manifest.json").write_text(
            json.dumps(
                {
                    "format": "testplat.contracts-manifest",
                    "formatVersion": "1.0",
                    "contracts": [
                        {
                            "id": "foundation.unsafe-integer",
                            "family": "foundation",
                            "version": "1.0",
                            "payload": "unsafe-integer.json",
                            "sha256": "sha256:" + ("0" * 64),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.assert_failure(self.run_tool("check"), "UNSAFE_INTEGER")

    def test_jcs_rejects_lone_surrogate_without_traceback(self) -> None:
        module = self.load_tool()
        self.assertEqual(module.jcs("\ud83d\ude00"), '"😀"')
        payload = self.root / "surrogate.json"
        payload.write_text('{"value":"\\ud800"}\n', encoding="utf-8")
        (self.root / "manifest.json").write_text(
            json.dumps(
                {
                    "format": "testplat.contracts-manifest",
                    "formatVersion": "1.0",
                    "contracts": [
                        {
                            "id": "foundation.surrogate",
                            "family": "foundation",
                            "version": "1.0",
                            "payload": "surrogate.json",
                            "sha256": "sha256:" + ("0" * 64),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        result = self.run_tool("check")
        self.assert_failure(result, "INVALID_UNICODE")

    def write_registry_entry(self, registry: str, entries_key: str, duplicate: bool = False) -> None:
        payload = self.root / "registry-payload.json"
        payload.write_text('{"name":"registry","value":1}\n', encoding="utf-8")
        entry = {
            "id": "foundation.registry-entry",
            "version": "1.0",
            "payload": "registry-payload.json",
            "sha256": self.load_tool().digest_payload(payload),
        }
        data = json.loads((self.root / registry).read_text(encoding="utf-8"))
        data[entries_key] = [entry, dict(entry)] if duplicate else [entry]
        (self.root / registry).write_text(json.dumps(data), encoding="utf-8")

    def test_auxiliary_registry_entries_validate_and_reject_duplicate_ids(self) -> None:
        registries = (
            ("schemas/manifest.json", "schemas"),
            ("fixtures/manifest.json", "fixtures"),
            ("errors/registry.json", "codes"),
        )
        for registry, entries_key in registries:
            with self.subTest(registry=registry):
                self.write_registry_entry(registry, entries_key)
                self.assertEqual(self.run_tool("check").returncode, 0)
                self.write_registry_entry(registry, entries_key, duplicate=True)
                self.assert_failure(self.run_tool("check"), "DUPLICATE_ID")
                data = json.loads((self.root / registry).read_text(encoding="utf-8"))
                data[entries_key] = []
                (self.root / registry).write_text(json.dumps(data), encoding="utf-8")

    def test_target_absolute_and_parent_paths_are_rejected(self) -> None:
        self.assert_failure(self.run_tool("check", str(self.root)), "PATH_ESCAPE")
        self.assert_failure(self.run_tool("check", "../outside"), "PATH_ESCAPE")

    def test_target_symlink_outside_contracts_is_rejected(self) -> None:
        outside = Path(self.tempdir.name) / "outside-target"
        outside.mkdir()
        (self.root / "target-link").symlink_to(outside, target_is_directory=True)
        self.assert_failure(self.run_tool("check", "target-link"), "PATH_ESCAPE")

    def test_required_directory_symlink_outside_contracts_is_rejected(self) -> None:
        outside = Path(self.tempdir.name) / "outside-schemas"
        outside.mkdir()
        shutil.rmtree(self.root / "schemas")
        (self.root / "schemas").symlink_to(outside, target_is_directory=True)
        self.assert_failure(self.run_tool("check"), "PATH_ESCAPE")

    def test_registry_symlink_outside_contracts_is_rejected(self) -> None:
        outside = Path(self.tempdir.name) / "outside-registry.json"
        outside.write_text("{}\n", encoding="utf-8")
        registry = self.root / "errors" / "registry.json"
        registry.unlink()
        registry.symlink_to(outside)
        self.assert_failure(self.run_tool("check"), "PATH_ESCAPE")

    def test_payload_symlink_outside_contracts_is_rejected(self) -> None:
        outside = Path(self.tempdir.name) / "outside-payload.json"
        outside.write_text('{"name":"outside"}\n', encoding="utf-8")
        (self.root / "payload-link.json").symlink_to(outside)
        (self.root / "manifest.json").write_text(
            json.dumps(
                {
                    "format": "testplat.contracts-manifest",
                    "formatVersion": "1.0",
                    "contracts": [
                        {
                            "id": "foundation.outside-payload",
                            "family": "foundation",
                            "version": "1.0",
                            "payload": "payload-link.json",
                            "sha256": "sha256:" + ("0" * 64),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.assert_failure(self.run_tool("check"), "PATH_ESCAPE")

    def test_make_target_is_data_not_shell_code(self) -> None:
        for command in ("contracts-check", "contracts-compat"):
            with self.subTest(command=command):
                marker = Path(self.tempdir.name) / f"make-injection-{command}"
                target = f"`touch {marker}`"
                result = subprocess.run(
                    ["make", command, f"TARGET={target}"],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertFalse(marker.exists(), msg=result.stderr)

                env_result = subprocess.run(
                    ["make", command],
                    cwd=ROOT,
                    env={**os.environ, "CONTRACTS_TARGET": target},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(env_result.returncode, 0, msg=env_result.stderr)
                self.assertIn("EMPTY_DIRECTORY", env_result.stderr, msg=env_result.stderr)
                self.assertFalse(marker.exists(), msg=env_result.stderr)


if __name__ == "__main__":
    unittest.main()
