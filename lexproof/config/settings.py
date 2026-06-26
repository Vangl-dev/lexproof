"""Configurações globais do LexProof."""

import json
from pathlib import Path
from typing import ClassVar

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação LexProof.

    Carrega configurações de variáveis de ambiente com prefixo LEXPROOF_
    e persiste em ~/.lexproof/settings.json.
    """

    model_config = SettingsConfigDict(
        env_prefix="LEXPROOF_",
        extra="ignore",
    )

    _instance: ClassVar["Settings | None"] = None

    theme: str = Field(default="system", description="Tema da interface: light, dark ou system")
    language: str = Field(default="pt_BR", description="Idioma da interface")
    last_directory: Path | None = Field(default=None, description="Último diretório acessado")
    favorite_directories: list[Path] = Field(default_factory=list, description="Diretórios favoritos")
    recent_files: list[Path] = Field(default_factory=list, description="Arquivos recentes")
    log_level: str = Field(default="INFO", description="Nível de log")
    log_directory: Path = Field(
        default_factory=lambda: Path.home() / ".lexproof" / "logs",
        description="Diretório de logs",
    )
    output_directory: Path = Field(
        default_factory=lambda: Path.home() / ".lexproof" / "output",
        description="Diretório de saída",
    )
    temp_directory: Path = Field(
        default_factory=lambda: Path.home() / ".lexproof" / "temp",
        description="Diretório temporário",
    )
    ocr_engine: str = Field(default="tesseract", description="Motor OCR: tesseract ou easyocr")
    hash_algorithms: list[str] = Field(
        default_factory=lambda: ["sha256", "sha3_512", "blake3"],
        description="Algoritmos de hash padrão",
    )
    auto_verify: bool = Field(default=True, description="Verificação automática ao abrir arquivo")

    @model_validator(mode="after")
    def _ensure_directories(self) -> "Settings":
        """Cria diretórios necessários se não existirem."""
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.temp_directory.mkdir(parents=True, exist_ok=True)
        return self

    @classmethod
    def get_instance(cls) -> "Settings":
        """Retorna a instância singleton de Settings."""
        if cls._instance is None:
            cls._instance = cls.load()
        return cls._instance

    @classmethod
    def load(cls) -> "Settings":
        """Carrega as configurações do arquivo JSON ou cria com padrões."""
        settings_path = Path.home() / ".lexproof" / "settings.json"
        if settings_path.exists():
            try:
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                return cls(**data)
            except (json.JSONDecodeError, Exception):
                return cls()
        return cls()

    def save(self) -> None:
        """Persiste as configurações em ~/.lexproof/settings.json."""
        settings_path = Path.home() / ".lexproof" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json")
        data.pop("_instance", None)
        settings_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
