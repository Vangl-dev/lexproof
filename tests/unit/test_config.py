"""Testes unitários para o módulo de configurações."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexproof.config.settings import Settings


@pytest.fixture
def fresh_settings(tmp_path: Path) -> Settings:
    """Cria um Settings isolado para testes, sem afetar o singleton global."""
    original_instance = Settings._instance
    Settings._instance = None
    settings = Settings(
        log_directory=tmp_path / "logs",
        output_directory=tmp_path / "output",
        temp_directory=tmp_path / "temp",
    )
    yield settings
    Settings._instance = original_instance


class TestDefaultSettings:
    def test_default_settings(self, fresh_settings):
        assert fresh_settings.theme == "system"
        assert fresh_settings.language == "pt_BR"
        assert fresh_settings.last_directory is None
        assert fresh_settings.favorite_directories == []
        assert fresh_settings.recent_files == []
        assert fresh_settings.log_level == "INFO"
        assert fresh_settings.ocr_engine == "tesseract"
        assert fresh_settings.auto_verify is True
        assert "sha256" in fresh_settings.hash_algorithms
        assert "sha3_512" in fresh_settings.hash_algorithms
        assert "blake3" in fresh_settings.hash_algorithms

    def test_default_directories_exist(self, fresh_settings):
        assert fresh_settings.log_directory.exists()
        assert fresh_settings.output_directory.exists()
        assert fresh_settings.temp_directory.exists()

    def test_settings_custom_values(self, tmp_path):
        original_instance = Settings._instance
        Settings._instance = None
        try:
            settings = Settings(
                theme="dark",
                language="en_US",
                log_level="DEBUG",
                ocr_engine="easyocr",
                auto_verify=False,
                log_directory=tmp_path / "custom_logs",
                output_directory=tmp_path / "custom_output",
                temp_directory=tmp_path / "custom_temp",
            )
            assert settings.theme == "dark"
            assert settings.language == "en_US"
            assert settings.log_level == "DEBUG"
            assert settings.ocr_engine == "easyocr"
            assert settings.auto_verify is False
        finally:
            Settings._instance = original_instance


class TestSaveLoadSettings:
    def test_save_load_settings(self, tmp_path):
        original_instance = Settings._instance
        Settings._instance = None
        try:
            settings = Settings(
                theme="dark",
                language="pt_BR",
                log_directory=tmp_path / "logs",
                output_directory=tmp_path / "output",
                temp_directory=tmp_path / "temp",
            )

            save_path = tmp_path / ".lexproof_test" / "settings.json"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            data = settings.model_dump(mode="json")
            data.pop("_instance", None)
            save_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )

            loaded_data = json.loads(save_path.read_text(encoding="utf-8"))
            assert loaded_data["theme"] == "dark"
            assert loaded_data["language"] == "pt_BR"
        finally:
            Settings._instance = original_instance

    def test_save_persists_theme(self, tmp_path):
        original_instance = Settings._instance
        Settings._instance = None
        try:
            settings = Settings(
                theme="light",
                log_directory=tmp_path / "logs",
                output_directory=tmp_path / "output",
                temp_directory=tmp_path / "temp",
            )
            save_path = tmp_path / "settings_test.json"
            data = settings.model_dump(mode="json")
            data.pop("_instance", None)
            save_path.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
            loaded = json.loads(save_path.read_text(encoding="utf-8"))
            assert loaded["theme"] == "light"
        finally:
            Settings._instance = original_instance


class TestSettingsSingleton:
    def test_settings_singleton(self, tmp_path):
        original_instance = Settings._instance
        Settings._instance = None
        try:
            s1 = Settings(
                log_directory=tmp_path / "l1",
                output_directory=tmp_path / "o1",
                temp_directory=tmp_path / "t1",
            )
            Settings._instance = s1
            s2 = Settings.get_instance()
            assert s1 is s2
        finally:
            Settings._instance = original_instance

    def test_get_instance_creates_new(self, tmp_path):
        original_instance = Settings._instance
        Settings._instance = None
        try:
            instance = Settings.get_instance()
            assert instance is not None
            assert isinstance(instance, Settings)
        finally:
            Settings._instance = original_instance
