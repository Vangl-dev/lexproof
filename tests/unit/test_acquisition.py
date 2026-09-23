"""Testes unitários para o módulo de aquisição forense."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from lexproof.acquisition.acquirer import ForensicAcquirer
from lexproof.acquisition.zip_handler import SecureZipHandler


class TestSecureZipHandler:
    """Testes para o handler seguro de ZIP."""

    def test_validate_valid_zip(self, tmp_path: Path) -> None:
        """Testa validação de ZIP válido."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "Hello, World!")

        handler = SecureZipHandler()
        assert handler.validate(zip_path) is True

    def test_validate_nonexistent_zip(self, tmp_path: Path) -> None:
        """Testa validação de ZIP inexistente."""
        zip_path = tmp_path / "nonexistent.zip"
        handler = SecureZipHandler()
        assert handler.validate(zip_path) is False

    def test_validate_invalid_extension(self, tmp_path: Path) -> None:
        """Testa validação com extensão inválida."""
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("Not a ZIP")

        handler = SecureZipHandler()
        assert handler.validate(txt_path) is False

    def test_validate_corrupted_zip(self, tmp_path: Path) -> None:
        """Testa validação de ZIP corrompido."""
        zip_path = tmp_path / "corrupted.zip"
        zip_path.write_bytes(b"PK\x03\x04 corrupted data")

        handler = SecureZipHandler()
        assert handler.validate(zip_path) is False

    def test_validate_path_traversal(self, tmp_path: Path) -> None:
        """Testa detecção de path traversal."""
        zip_path = tmp_path / "traversal.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../../etc/passwd", "malicious")

        handler = SecureZipHandler()
        assert handler.validate(zip_path) is False
        assert any("Path traversal" in e for e in handler.errors)

    def test_validate_too_many_files(self, tmp_path: Path) -> None:
        """Testa limite de número de arquivos."""
        zip_path = tmp_path / "many_files.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(10001):
                zf.writestr(f"file_{i}.txt", f"content {i}")

        handler = SecureZipHandler(max_files=10000)
        assert handler.validate(zip_path) is False

    def test_validate_zip_bomb(self, tmp_path: Path) -> None:
        """Testa detecção de ZIP Bomb."""
        zip_path = tmp_path / "bomb.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Criar arquivo comprimido com alta razão
            content = "A" * 1000000
            zf.writestr("bomb.txt", content)

        handler = SecureZipHandler(max_compression_ratio=10)
        assert handler.validate(zip_path) is True  # Válido mas com aviso
        assert len(handler.warnings) > 0

    def test_extract_safe(self, tmp_path: Path) -> None:
        """Testa extração segura."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "Content 1")
            zf.writestr("file2.txt", "Content 2")

        extract_dir = tmp_path / "extracted"
        handler = SecureZipHandler()
        extracted = handler.extract(zip_path, extract_dir)

        assert len(extracted) == 2
        assert all(f.exists() for f in extracted)

    def test_get_contents(self, tmp_path: Path) -> None:
        """Testa listagem de conteúdo."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "Content 1")
            zf.writestr("dir/file2.txt", "Content 2")

        handler = SecureZipHandler()
        contents = handler.get_contents(zip_path)

        assert len(contents) == 2
        assert any(c.name == "file1.txt" for c in contents)
        assert any(c.name == "dir/file2.txt" for c in contents)


class TestForensicAcquirer:
    """Testes para o aquisitor forense."""

    def test_acquire_single_file(self, tmp_path: Path) -> None:
        """Testa aquisição de arquivo único."""
        # Criar arquivo de teste
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        # Criar aquisitor
        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)

        # Adquirir
        results = acquirer.acquire([test_file])

        assert len(results) == 1
        assert results[0].evidence.file_name == "test.txt"
        assert "sha256" in results[0].hashes
        assert "blake3" in results[0].hashes

    def test_acquire_image(self, tmp_path: Path) -> None:
        """Testa aquisição de imagem."""
        # Criar imagem de teste
        from PIL import Image
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(img_path)

        # Criar aquisitor
        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)

        # Adquirir
        results = acquirer.acquire([img_path])

        assert len(results) == 1
        assert results[0].evidence.evidence_type.value == "image"

    def test_acquire_whatsapp_zip(self, tmp_path: Path) -> None:
        """Testa aquisição de ZIP WhatsApp."""
        # Criar ZIP com exportação WhatsApp
        zip_path = tmp_path / "whatsapp.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("_chat.txt", "Mensagens e chamadas são criptografadas\n15/03/2024 10:00, João: Olá!")
            zf.writestr("IMG-20240315-WA0001.jpg", b"fake image data")

        # Criar aquisitor
        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)

        # Adquirir
        results = acquirer.acquire([zip_path])

        assert len(results) == 1
        assert results[0].zip_manifest is not None
        assert results[0].zip_manifest.file_count == 2

    def test_acquire_multiple_files(self, tmp_path: Path) -> None:
        """Testa aquisição de múltiplos arquivos."""
        # Criar arquivos
        files = []
        for i in range(3):
            f = tmp_path / f"file_{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)

        # Criar aquisitor
        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)

        # Adquirir
        results = acquirer.acquire(files)

        assert len(results) == 3

    def test_session_structure_created(self, tmp_path: Path) -> None:
        """Testa criação da estrutura de sessão."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")

        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)
        acquirer.acquire([test_file])

        # Verificar estrutura
        assert (output_dir / "evidence" / "original").exists()
        assert (output_dir / "evidence" / "derived").exists()
        assert (output_dir / "logs").exists()
        assert (output_dir / "temp").exists()

    def test_session_files_generated(self, tmp_path: Path) -> None:
        """Testa geração de arquivos de sessão."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")

        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)
        acquirer.acquire([test_file])

        # Verificar arquivos
        assert (output_dir / "session.json").exists()
        assert (output_dir / "pipeline.json").exists()
        assert (output_dir / "hashes.json").exists()
        assert (output_dir / "metadata.json").exists()

    def test_zip_manifest_generated(self, tmp_path: Path) -> None:
        """Testa geração de manifesto ZIP."""
        # Criar ZIP
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "Content 1")
            zf.writestr("file2.txt", "Content 2")

        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)
        results = acquirer.acquire([zip_path])

        # Verificar manifesto
        assert (output_dir / "zip_manifest.json").exists()
        assert results[0].zip_manifest is not None

    def test_pipeline_tracked(self, tmp_path: Path) -> None:
        """Testa rastreamento do pipeline."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")

        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)
        acquirer.acquire([test_file])

        # Verificar pipeline
        import json
        pipeline_path = output_dir / "pipeline.json"
        pipeline_data = json.loads(pipeline_path.read_text())

        assert "steps" in pipeline_data
        assert len(pipeline_data["steps"]) > 0

    def test_original_not_modified(self, tmp_path: Path) -> None:
        """Testa que o arquivo original não é modificado."""
        test_file = tmp_path / "test.txt"
        original_content = "Original content"
        test_file.write_text(original_content)
        original_hash = test_file.read_text()

        output_dir = tmp_path / "session"
        acquirer = ForensicAcquirer(output_dir)
        acquirer.acquire([test_file])

        # Verificar que o conteúdo não mudou
        assert test_file.read_text() == original_hash
