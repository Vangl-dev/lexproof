"""Geração e validação de manifestos de evidências."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from lexproof.models import HashResult

MANIFEST_VERSION = "1.0.0"


class ManifestGenerator:
    """Gera e valida manifestos de integridade de arquivos."""

    def generate(
        self, file_hashes: list[HashResult], metadata: dict
    ) -> dict:
        """Gera a estrutura de dados de um manifesto.

        Args:
            file_hashes: Lista de resultados de hash dos arquivos.
            metadata: Metadados adicionais (caso, autor, descrição, etc.).

        Returns:
            Dicionário estruturado do manifesto.
        """
        file_entries = []
        all_hash_strings: list[str] = []

        for hr in file_hashes:
            entry = {
                "file_path": str(hr.file_path),
                "algorithm": hr.algorithm.value,
                "hash_value": hr.hash_value,
                "file_size": hr.file_size,
            }
            file_entries.append(entry)
            all_hash_strings.append(hr.hash_value)

        global_hash = ""
        if all_hash_strings:
            combined = "".join(sorted(all_hash_strings))
            global_hash = hashlib.sha256(
                combined.encode("utf-8")
            ).hexdigest()

        return {
            "version": MANIFEST_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "global_hash": global_hash,
            "file_count": len(file_entries),
            "files": file_entries,
            "metadata": metadata,
        }

    def create_manifest_file(self, data: dict, output_path: Path) -> Path:
        """Persiste o manifesto em um arquivo JSON.

        Args:
            data: Dicionário do manifesto (saída de generate()).
            output_path: Caminho do arquivo de saída.

        Returns:
            Caminho absoluto do arquivo criado.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        output_path.write_text(content, encoding="utf-8")
        return output_path.resolve()

    @staticmethod
    def validate_manifest(manifest_path: Path) -> bool:
        """Valida a integridade e estrutura de um manifesto existente.

        Verifica:
        - O arquivo existe e é JSON válido.
        - Possui campos obrigatórios (version, timestamp, files, global_hash).
        - Recalcula o global_hash e compara com o armazenado.

        Args:
            manifest_path: Caminho do arquivo de manifesto.

        Returns:
            True se o manifesto for válido, False caso contrário.
        """
        if not manifest_path.is_file():
            return False

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False

        required_fields = {"version", "timestamp", "files", "global_hash"}
        if not required_fields.issubset(data.keys()):
            return False

        if not isinstance(data["files"], list) or not data["files"]:
            return False

        stored_hash = data.get("global_hash", "")
        all_hash_strings = [
            entry["hash_value"]
            for entry in data["files"]
            if "hash_value" in entry
        ]
        if not all_hash_strings:
            return False

        combined = "".join(sorted(all_hash_strings))
        computed_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        return computed_hash == stored_hash
