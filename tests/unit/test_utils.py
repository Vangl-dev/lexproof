"""Testes unitários para funções utilitárias."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lexproof.utils.file_utils import (
    calculate_directory_size,
    ensure_directory,
    get_file_hash,
    get_file_info,
    get_mime_type,
    is_supported_type,
    safe_filename,
)


class TestSafeFilename:
    def test_safe_filename_basic(self):
        result = safe_filename("documento.pdf")
        assert result == "documento.pdf"

    def test_safe_filename_with_spaces(self):
        result = safe_filename("meu documento.pdf")
        assert " " not in result
        assert "_" in result

    def test_safe_filename_special_chars(self):
        result = safe_filename("arquivo@#$.txt")
        assert "@" not in result
        assert "#" not in result

    def test_safe_filename_unicode(self):
        result = safe_filename("arquivo_unico_çãõ.txt")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_safe_filename_empty(self):
        result = safe_filename("")
        assert result == "unnamed"

    def test_safe_filename_long_name(self):
        long_name = "a" * 300
        result = safe_filename(long_name)
        assert len(result) <= 200

    def test_safe_filename_only_special_chars(self):
        result = safe_filename("@#$%^&*()")
        assert result == "unnamed" or len(result) > 0

    def test_safe_filename_multiple_underscores(self):
        result = safe_filename("a  b   c    d")
        assert "__" not in result


class TestGetMimeType:
    def test_get_mime_type_txt(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")
        assert get_mime_type(file_path) == "text/plain"

    def test_get_mime_type_json(self, tmp_path):
        file_path = tmp_path / "test.json"
        file_path.write_text("{}")
        assert get_mime_type(file_path) == "application/json"

    def test_get_mime_type_unknown(self, tmp_path):
        file_path = tmp_path / "test.xyz123"
        file_path.write_text("test")
        assert get_mime_type(file_path) == "application/octet-stream"

    def test_get_mime_type_html(self, tmp_path):
        file_path = tmp_path / "test.html"
        file_path.write_text("<html></html>")
        assert get_mime_type(file_path) == "text/html"

    def test_get_mime_type_csv(self, tmp_path):
        file_path = tmp_path / "test.csv"
        file_path.write_text("a,b,c")
        assert get_mime_type(file_path) == "text/csv"


class TestEnsureDirectory:
    def test_ensure_directory(self, tmp_path):
        new_dir = tmp_path / "new_directory"
        result = ensure_directory(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()
        assert result == new_dir

    def test_ensure_directory_nested(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        ensure_directory(nested)
        assert nested.exists()
        assert nested.is_dir()

    def test_ensure_directory_existing(self, tmp_path):
        result = ensure_directory(tmp_path)
        assert tmp_path.exists()
        assert result == tmp_path


class TestCalculateDirectorySize:
    def test_calculate_directory_size(self, tmp_path):
        (tmp_path / "file1.txt").write_text("hello")
        (tmp_path / "file2.txt").write_text("world!")
        total = calculate_directory_size(tmp_path)
        assert total > 0

    def test_calculate_directory_size_nested(self, tmp_path):
        (tmp_path / "file1.txt").write_text("hello")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "file2.txt").write_text("world!")
        total = calculate_directory_size(tmp_path)
        assert total > 0

    def test_calculate_directory_size_empty(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        total = calculate_directory_size(empty_dir)
        assert total == 0

    def test_calculate_directory_size_not_a_directory(self, tmp_path):
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(NotADirectoryError):
            calculate_directory_size(file_path)

    def test_calculate_directory_size准确性(self, tmp_path):
        content1 = "hello"
        content2 = "world!"
        (tmp_path / "a.txt").write_text(content1)
        (tmp_path / "b.txt").write_text(content2)
        expected = len(content1.encode()) + len(content2.encode())
        assert calculate_directory_size(tmp_path) == expected


class TestGetFileHash:
    def test_get_file_hash(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("test content")
        import hashlib

        expected = hashlib.sha256(b"test content").hexdigest()
        assert get_file_hash(file_path) == expected

    def test_get_file_hash_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            get_file_hash(tmp_path / "nonexistent.txt")

    def test_get_file_hash_md5(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")
        import hashlib

        expected = hashlib.md5(b"test").hexdigest()
        result = get_file_hash(file_path, algorithm="md5")
        assert result == expected


class TestGetFileInfo:
    def test_get_file_info(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello")
        info = get_file_info(file_path)
        assert info["name"] == "test.txt"
        assert info["extension"] == ".txt"
        assert info["size"] == 5
        assert info["is_file"] is True
        assert info["is_directory"] is False
        assert "absolute_path" in info


class TestIsSupportedType:
    def test_is_supported_type_image(self, tmp_path):
        file_path = tmp_path / "photo.jpg"
        assert is_supported_type(file_path, "image") is True

    def test_is_supported_type_document(self, tmp_path):
        file_path = tmp_path / "doc.pdf"
        assert is_supported_type(file_path, "document") is True

    def test_is_supported_type_text(self, tmp_path):
        file_path = tmp_path / "data.json"
        assert is_supported_type(file_path, "text") is True

    def test_is_supported_type_video(self, tmp_path):
        file_path = tmp_path / "video.mp4"
        assert is_supported_type(file_path, "video") is True

    def test_is_supported_type_archive(self, tmp_path):
        file_path = tmp_path / "archive.zip"
        assert is_supported_type(file_path, "archive") is True

    def test_is_supported_type_unknown_category(self, tmp_path):
        file_path = tmp_path / "test.txt"
        assert is_supported_type(file_path, "unknown") is False

    def test_is_supported_type_wrong_category(self, tmp_path):
        file_path = tmp_path / "photo.jpg"
        assert is_supported_type(file_path, "document") is False

    def test_is_supported_type_case_insensitive(self, tmp_path):
        file_path = tmp_path / "photo.jpg"
        assert is_supported_type(file_path, "IMAGE") is True
