"""Testes unitários para o módulo de hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from lexproof.crypto.hasher import FileHasher
from lexproof.models.hash_result import HashAlgorithm, HashResult


@pytest.fixture
def hasher() -> FileHasher:
    return FileHasher()


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Hello, LexProof!", encoding="utf-8")
    return file_path


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "empty_file.txt"
    file_path.write_text("", encoding="utf-8")
    return file_path


class TestComputeSha256:
    def test_compute_sha256(self, hasher, sample_file):
        result = hasher.compute_hash(sample_file, HashAlgorithm.SHA256)
        assert isinstance(result, HashResult)
        assert result.algorithm == HashAlgorithm.SHA256
        assert len(result.hash_value) == 64
        assert result.file_size == 16

    def test_sha256_deterministic(self, hasher, sample_file):
        result1 = hasher.compute_hash(sample_file, HashAlgorithm.SHA256)
        result2 = hasher.compute_hash(sample_file, HashAlgorithm.SHA256)
        assert result1.hash_value == result2.hash_value

    def test_sha256_known_content(self, hasher, sample_file):
        result = hasher.compute_hash(sample_file, HashAlgorithm.SHA256)
        expected = hashlib.sha256(b"Hello, LexProof!").hexdigest()
        assert result.hash_value == expected


class TestComputeSha3_512:
    def test_compute_sha3_512(self, hasher, sample_file):
        result = hasher.compute_hash(sample_file, HashAlgorithm.SHA3_512)
        assert isinstance(result, HashResult)
        assert result.algorithm == HashAlgorithm.SHA3_512
        assert len(result.hash_value) == 128

    def test_sha3_512_deterministic(self, hasher, sample_file):
        result1 = hasher.compute_hash(sample_file, HashAlgorithm.SHA3_512)
        result2 = hasher.compute_hash(sample_file, HashAlgorithm.SHA3_512)
        assert result1.hash_value == result2.hash_value

    def test_sha3_512_known_content(self, hasher, sample_file):
        result = hasher.compute_hash(sample_file, HashAlgorithm.SHA3_512)
        expected = hashlib.sha3_512(b"Hello, LexProof!").hexdigest()
        assert result.hash_value == expected


class TestComputeBlake3:
    def test_compute_blake3(self, hasher, sample_file):
        result = hasher.compute_hash(sample_file, HashAlgorithm.BLAKE3)
        assert isinstance(result, HashResult)
        assert result.algorithm == HashAlgorithm.BLAKE3
        assert len(result.hash_value) == 64

    def test_blake3_deterministic(self, hasher, sample_file):
        result1 = hasher.compute_hash(sample_file, HashAlgorithm.BLAKE3)
        result2 = hasher.compute_hash(sample_file, HashAlgorithm.BLAKE3)
        assert result1.hash_value == result2.hash_value


class TestComputeAllHashes:
    def test_compute_all_hashes(self, hasher, sample_file):
        results = hasher.compute_all_hashes(sample_file)
        assert len(results) == 3
        algorithms = {r.algorithm for r in results}
        assert HashAlgorithm.SHA256 in algorithms
        assert HashAlgorithm.SHA3_512 in algorithms
        assert HashAlgorithm.BLAKE3 in algorithms

    def test_all_hashes_different(self, hasher, sample_file):
        results = hasher.compute_all_hashes(sample_file)
        hash_values = [r.hash_value for r in results]
        assert len(set(hash_values)) == 3


class TestComputeMerkleRoot:
    def test_merkle_root_empty(self):
        result = FileHasher.compute_merkle_root([])
        assert result == ""

    def test_merkle_root_single(self):
        hashes = ["abc123"]
        result = FileHasher.compute_merkle_root(hashes)
        assert result == "abc123"

    def test_merkle_root_two(self):
        hashes = ["aaa", "bbb"]
        result = FileHasher.compute_merkle_root(hashes)
        expected = hashlib.sha256(("aaa" + "bbb").encode("utf-8")).hexdigest()
        assert result == expected

    def test_merkle_root_odd_number(self):
        hashes = ["aaa", "bbb", "ccc"]
        result = FileHasher.compute_merkle_root(hashes)
        assert len(result) == 64

    def test_merkle_root_four(self):
        hashes = ["a", "b", "c", "d"]
        result = FileHasher.compute_merkle_root(hashes)
        assert len(result) == 64
        assert result != ""

    def test_merkle_root_deterministic(self):
        hashes = ["a", "b", "c"]
        r1 = FileHasher.compute_merkle_root(hashes)
        r2 = FileHasher.compute_merkle_root(hashes)
        assert r1 == r2

    def test_merkle_root_different_input_different_output(self):
        r1 = FileHasher.compute_merkle_root(["a", "b"])
        r2 = FileHasher.compute_merkle_root(["a", "c"])
        assert r1 != r2


class TestComputeGlobalHash:
    def test_compute_global_hash(self, hasher, tmp_path):
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding="utf-8")
        file2 = tmp_path / "file2.txt"
        file2.write_text("content2", encoding="utf-8")

        result = hasher.compute_global_hash([file1, file2])
        assert len(result) == 64
        assert result != ""

    def test_compute_global_hash_single_file(self, hasher, sample_file):
        result = hasher.compute_global_hash([sample_file])
        assert len(result) == 64

    def test_compute_global_hash_deterministic(self, hasher, sample_file):
        r1 = hasher.compute_global_hash([sample_file])
        r2 = hasher.compute_global_hash([sample_file])
        assert r1 == r2

    def test_compute_global_hash_different_files_different_result(self, hasher, tmp_path):
        file1 = tmp_path / "a.txt"
        file1.write_text("aaa", encoding="utf-8")
        file2 = tmp_path / "b.txt"
        file2.write_text("bbb", encoding="utf-8")

        r1 = hasher.compute_global_hash([file1])
        r2 = hasher.compute_global_hash([file2])
        assert r1 != r2


class TestHashEmptyFile:
    def test_hash_empty_file_sha256(self, hasher, empty_file):
        result = hasher.compute_hash(empty_file, HashAlgorithm.SHA256)
        expected = hashlib.sha256(b"").hexdigest()
        assert result.hash_value == expected
        assert result.file_size == 0

    def test_hash_empty_file_blake3(self, hasher, empty_file):
        result = hasher.compute_hash(empty_file, HashAlgorithm.BLAKE3)
        assert len(result.hash_value) == 64


class TestHashLargeFile:
    def test_hash_large_file(self, hasher, tmp_path):
        large_file = tmp_path / "large.bin"
        content = b"X" * (1024 * 1024)
        large_file.write_bytes(content)

        result = hasher.compute_hash(large_file, HashAlgorithm.SHA256)
        expected = hashlib.sha256(content).hexdigest()
        assert result.hash_value == expected
        assert result.file_size == 1024 * 1024

    def test_hash_file_not_found(self, hasher, tmp_path):
        with pytest.raises(FileNotFoundError):
            hasher.compute_hash(tmp_path / "nonexistent.txt", HashAlgorithm.SHA256)

    def test_hash_result_has_correct_file_path(self, hasher, sample_file):
        result = hasher.compute_hash(sample_file, HashAlgorithm.SHA256)
        assert Path(result.file_path) == sample_file.resolve()
