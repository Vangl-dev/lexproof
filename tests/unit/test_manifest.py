"""Testes unitários para o módulo de manifesto."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lexproof.crypto.manifest import MANIFEST_VERSION, ManifestGenerator
from lexproof.models.hash_result import HashAlgorithm, HashResult


@pytest.fixture
def generator() -> ManifestGenerator:
    return ManifestGenerator()


@pytest.fixture
def sample_hash_results(tmp_path: Path) -> list[HashResult]:
    file1 = tmp_path / "file1.txt"
    file1.write_text("content1", encoding="utf-8")
    file2 = tmp_path / "file2.txt"
    file2.write_text("content2", encoding="utf-8")

    return [
        HashResult(
            algorithm=HashAlgorithm.SHA256,
            hash_value=hashlib.sha256(b"content1").hexdigest(),
            file_path=str(file1),
            file_size=8,
        ),
        HashResult(
            algorithm=HashAlgorithm.SHA256,
            hash_value=hashlib.sha256(b"content2").hexdigest(),
            file_path=str(file2),
            file_size=8,
        ),
    ]


class TestGenerateManifest:
    def test_generate_manifest(self, generator, sample_hash_results):
        metadata = {"case_number": "2024-001", "author": "Teste"}
        manifest = generator.generate(sample_hash_results, metadata)

        assert manifest["version"] == MANIFEST_VERSION
        assert "timestamp" in manifest
        assert manifest["global_hash"] != ""
        assert manifest["file_count"] == 2
        assert len(manifest["files"]) == 2
        assert manifest["metadata"]["case_number"] == "2024-001"

    def test_generate_manifest_file_entries(self, generator, sample_hash_results):
        manifest = generator.generate(sample_hash_results, {})

        for entry in manifest["files"]:
            assert "file_path" in entry
            assert "algorithm" in entry
            assert "hash_value" in entry
            assert "file_size" in entry

    def test_generate_manifest_empty_hashes(self, generator):
        manifest = generator.generate([], {})
        assert manifest["file_count"] == 0
        assert manifest["global_hash"] == ""
        assert manifest["files"] == []

    def test_generate_manifest_single_file(self, generator, sample_hash_results):
        manifest = generator.generate([sample_hash_results[0]], {})
        assert manifest["file_count"] == 1

    def test_generate_manifest_global_hash_reproducible(self, generator, sample_hash_results):
        m1 = generator.generate(sample_hash_results, {"a": 1})
        m2 = generator.generate(sample_hash_results, {"a": 1})
        assert m1["global_hash"] == m2["global_hash"]


class TestCreateManifestFile:
    def test_create_manifest_file(self, generator, tmp_path):
        output_path = tmp_path / "manifest.json"
        data = {
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z",
            "global_hash": "abc123",
            "file_count": 1,
            "files": [{"hash_value": "abc123"}],
        }
        result = generator.create_manifest_file(data, output_path)

        assert result.exists()
        loaded = json.loads(result.read_text(encoding="utf-8"))
        assert loaded["version"] == "1.0.0"
        assert loaded["global_hash"] == "abc123"

    def test_create_manifest_file_creates_parent_dirs(self, generator, tmp_path):
        output_path = tmp_path / "nested" / "dir" / "manifest.json"
        data = {"version": "1.0.0"}
        result = generator.create_manifest_file(data, output_path)
        assert result.exists()

    def test_create_manifest_file_returns_resolved_path(self, generator, tmp_path):
        output_path = tmp_path / "manifest.json"
        data = {"version": "1.0.0"}
        result = generator.create_manifest_file(data, output_path)
        assert result.is_absolute()


class TestValidateManifest:
    def test_validate_manifest_valid(self, generator, tmp_path):
        file1 = tmp_path / "file1.txt"
        file1.write_text("test", encoding="utf-8")
        hash_results = [
            HashResult(
                algorithm=HashAlgorithm.SHA256,
                hash_value=hashlib.sha256(b"test").hexdigest(),
                file_path=str(file1),
                file_size=4,
            )
        ]
        manifest_data = generator.generate(hash_results, {"case": "test"})
        manifest_path = tmp_path / "manifest.json"
        generator.create_manifest_file(manifest_data, manifest_path)

        assert ManifestGenerator.validate_manifest(manifest_path) is True

    def test_validate_manifest_nonexistent_file(self, tmp_path):
        assert ManifestGenerator.validate_manifest(tmp_path / "nonexistent.json") is False

    def test_validate_manifest_invalid_json(self, tmp_path):
        manifest_path = tmp_path / "invalid.json"
        manifest_path.write_text("not json {{{", encoding="utf-8")
        assert ManifestGenerator.validate_manifest(manifest_path) is False

    def test_validate_manifest_missing_fields(self, tmp_path):
        manifest_path = tmp_path / "incomplete.json"
        manifest_path.write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
        assert ManifestGenerator.validate_manifest(manifest_path) is False

    def test_validate_manifest_empty_files_list(self, tmp_path):
        manifest_path = tmp_path / "empty_files.json"
        data = {
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z",
            "global_hash": "abc",
            "files": [],
        }
        manifest_path.write_text(json.dumps(data), encoding="utf-8")
        assert ManifestGenerator.validate_manifest(manifest_path) is False

    def test_validate_manifest_tampered_hash(self, generator, tmp_path):
        file1 = tmp_path / "file1.txt"
        file1.write_text("test", encoding="utf-8")
        hash_results = [
            HashResult(
                algorithm=HashAlgorithm.SHA256,
                hash_value=hashlib.sha256(b"test").hexdigest(),
                file_path=str(file1),
                file_size=4,
            )
        ]
        manifest_data = generator.generate(hash_results, {})
        manifest_path = tmp_path / "manifest.json"
        generator.create_manifest_file(manifest_data, manifest_path)

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["global_hash"] = "tampered_hash"
        manifest_path.write_text(json.dumps(data), encoding="utf-8")

        assert ManifestGenerator.validate_manifest(manifest_path) is False

    def test_validate_manifest_wrong_global_hash(self, generator, tmp_path):
        file1 = tmp_path / "file1.txt"
        file1.write_text("test", encoding="utf-8")
        hash_results = [
            HashResult(
                algorithm=HashAlgorithm.SHA256,
                hash_value=hashlib.sha256(b"test").hexdigest(),
                file_path=str(file1),
                file_size=4,
            )
        ]
        manifest_data = generator.generate(hash_results, {})
        manifest_data["global_hash"] = "0" * 64
        manifest_path = tmp_path / "manifest.json"
        generator.create_manifest_file(manifest_data, manifest_path)

        assert ManifestGenerator.validate_manifest(manifest_path) is False
