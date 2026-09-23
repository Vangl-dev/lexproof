"""Gerenciador de sessões de caso do LexProof."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from lexproof.config.paths import Paths
from lexproof.core.constants import (
    DEFAULT_ENCODING,
    HASH_ALGORITHMS,
    SESSION_FILE_EXTENSION,
)
from lexproof.crypto.hasher import FileHasher
from lexproof.models.case import PreservationSession, SessionMetadata
from lexproof.models.custody import CustodyChain, CustodyEvent, CustodyEventType
from lexproof.models.evidence import Evidence, EvidenceType
from lexproof.models.hash_result import HashAlgorithm, HashResult
from lexproof.utils.file_utils import EXTENSION_EVIDENCE_TYPE_MAP, detect_evidence_type

logger = logging.getLogger(__name__)

# Mantido para retrocompatibilidade
_EVIDENCE_TYPE_MAP: dict[str, EvidenceType] = EXTENSION_EVIDENCE_TYPE_MAP

_ALGORITHM_MAP: dict[str, HashAlgorithm] = {
    "sha256": HashAlgorithm.SHA256,
    "sha3_512": HashAlgorithm.SHA3_512,
    "blake3": HashAlgorithm.BLAKE3,
}


class SessionManager:
    """Gerencia a sessão atual de trabalho com um caso.

    Responsável por rastrear evidências importadas, hashes calculados
    e manter a cadeia de custódia automaticamente.
    """

    def __init__(self) -> None:
        self._session: PreservationSession = PreservationSession()
        self._session_path: Optional[Path] = None
        self._is_active: bool = False
        self._hash_cache: dict[str, dict[str, str]] = {}
        self._hasher: FileHasher = FileHasher()

    @property
    def is_active(self) -> bool:
        """Indica se há uma sessão ativa."""
        return self._is_active

    @property
    def session(self) -> PreservationSession:
        """Retorna a PreservationSession da sessão atual."""
        return self._session

    @property
    def case_file(self) -> PreservationSession:
        """Retorna a PreservationSession (compatibilidade)."""
        return self._session

    @property
    def session_path(self) -> Optional[Path]:
        """Caminho do arquivo de sessão salvo."""
        return self._session_path

    def start_session(
        self,
        case_number: str = "",
        description: str = "",
        client_name: str = "",
        responsible_technician: str = "",
        save_path: Optional[Path] = None,
    ) -> PreservationSession:
        """Inicia uma nova sessão de preservação.

        Se ``save_path`` não for informado, usa o caminho permanente padrão
        em ``~/.lexproof/cases/<session_code>/case.lexproof.json`` e grava
        a sessão imediatamente.

        Args:
            case_number: Número do processo.
            description: Descrição do caso.
            client_name: Nome do cliente.
            responsible_technician: Responsável técnico.
            save_path: Caminho para salvar o arquivo de sessão.

        Returns:
            A PreservationSession criada.
        """
        self._session = PreservationSession(
            metadata=SessionMetadata(
                case_number=case_number,
                description=description,
                client_name=client_name,
                responsible_technician=responsible_technician,
            )
        )
        if save_path is None:
            save_path = Paths.session_file_path(self._session.session_code)
        self._session_path = save_path
        self._is_active = True
        self._hash_cache.clear()

        logger.info(
            "Sessão iniciada: %s - %s",
            self._session.session_code,
            description or "Nova Sessão",
        )

        self.save_session(save_path)

        return self._session

    def load_session(self, path: Path) -> PreservationSession:
        """Carrega uma sessão salva de um arquivo JSON.

        Args:
            path: Caminho do arquivo de sessão.

        Returns:
            A PreservationSession carregada.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ValueError: Se o conteúdo do arquivo for inválido.
        """
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de sessão não encontrado: {path}")

        try:
            data = json.loads(path.read_text(encoding=DEFAULT_ENCODING))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido no arquivo de sessão: {exc}") from exc

        self._session = PreservationSession.model_validate(data)
        self._session_path = self._normalize_session_path(path)
        self._is_active = True
        self._rebuild_hash_cache()

        logger.info(
            "Sessão carregada: %s de %s",
            self._session.session_code,
            self._session_path,
        )
        return self._session

    @staticmethod
    def _normalize_session_path(path: Path) -> Path:
        """Garante o sufixo ``.lexproof.json`` sem duplicar a extensão.

        Usa ``endswith`` porque ``Path.suffix`` só retorna ``.json``
        e ``with_suffix(SESSION_FILE_EXTENSION)`` em re-saves duplicaria
        o sufixo (ex.: ``case.lexproof.lexproof.json``).
        """
        if not path.name.endswith(SESSION_FILE_EXTENSION):
            # with_suffix substitui o último sufixo (.json → .lexproof.json)
            # ou acrescenta se não houver sufixo multi-ponto.
            path = path.with_suffix(SESSION_FILE_EXTENSION)
        return path

    def save_session(self, path: Optional[Path] = None) -> Path:
        """Salva a sessão atual em um arquivo JSON.

        Args:
            path: Caminho de destino. Se None, usa o caminho existente.

        Returns:
            Caminho do arquivo salvo.

        Raises:
            RuntimeError: Se nenhum caminho foi especificado e nenhum existe.
        """
        target = path or self._session_path
        if target is None:
            raise RuntimeError("Nenhum caminho de sessão especificado")

        target = self._normalize_session_path(target)

        target.parent.mkdir(parents=True, exist_ok=True)
        data = self._session.model_dump(mode="json")
        target.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding=DEFAULT_ENCODING,
        )
        self._session_path = target

        logger.info("Sessão salva em %s", target)
        return target

    def add_evidence(
        self,
        file_path: Path,
        *,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> Evidence:
        """Importa um arquivo de evidência para a sessão atual.

        Quando a sessão tem caminho persistente, copia o arquivo para
        ``evidence/original/`` do caso (COPY, não MOVE) e registra o
        Evidence apontando para a cópia permanente. O original do usuário
        não é alterado. Colisões de nome usam sufixo `` (n)``.

        Args:
            file_path: Caminho do arquivo de evidência (original do usuário).
            description: Descrição opcional.
            tags: Tags para organização.

        Returns:
            A Evidence criada (file_path = cópia permanente, se aplicável).

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            RuntimeError: Se não houver sessão ativa.
        """
        if not self._is_active:
            raise RuntimeError("Nenhuma sessão ativa. Chame start_session() primeiro.")

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Não é um arquivo: {file_path}")

        source = file_path.resolve()
        stored = self._preserve_original(source)

        file_size = stored.stat().st_size
        evidence_type = detect_evidence_type(stored)

        sha256_hash = self._compute_hash(stored, "sha256")
        try:
            blake3_hash = self._compute_hash(stored, "blake3")
        except Exception as e:
            logger.warning("BLAKE3 indisponivel para %s: %s", stored.name, e)
            blake3_hash = ""

        evidence = Evidence(
            file_path=stored,
            file_name=stored.name,
            file_size=file_size,
            evidence_type=evidence_type,
            sha256=sha256_hash,
            blake3=blake3_hash,
            description=description,
            tags=tags or [],
        )

        self._session.add_evidence(evidence)

        self._compute_all_hashes(stored)

        logger.info(
            "Evidência adicionada: %s (%s, %d bytes) -> %s",
            stored.name,
            evidence_type.value,
            file_size,
            stored,
        )

        if self._session_path is not None:
            self.save_session()

        return evidence

    def _evidence_original_dir(self) -> Path:
        """Diretório permanente de originais do caso atual.

        Usa o pai do arquivo de sessão quando houver caminho persistente;
        caso contrário, ``Paths.evidence_original_dir`` do session_code.
        """
        if self._session_path is not None:
            base = self._session_path.parent
        else:
            base = Paths.case_dir(self._session.session_code)
        path = base / "evidence" / "original"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _unique_dest(dest_dir: Path, filename: str) -> Path:
        """Retorna caminho livre de colisão de forma determinística.

        Estratégia: ``conversa.zip``, ``conversa (1).zip``, ``conversa (2).zip``...
        Nunca sobrescreve arquivo existente.
        """
        candidate = dest_dir / filename
        if not candidate.exists():
            return candidate
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while True:
            candidate = dest_dir / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _preserve_original(self, source: Path) -> Path:
        """Copia o arquivo original para o diretório permanente do caso.

        Se o arquivo já estiver dentro de ``evidence/original/``, retorna
        o próprio caminho (sem copiar de novo).

        Args:
            source: Caminho absoluto do arquivo de origem.

        Returns:
            Caminho da cópia permanente (ou de ``source`` se já é permanente).
        """
        if self._session_path is None:
            # Sem sessão persistida: usa o caminho original (comportamento antigo).
            return source

        original_dir = self._evidence_original_dir()
        try:
            source.relative_to(original_dir.resolve())
            return source
        except ValueError:
            pass

        dest = self._unique_dest(original_dir, source.name)
        shutil.copy2(source, dest)
        logger.info("Evidência copiada: %s -> %s", source, dest)
        return dest

    def compute_file_hash(self, file_path: Path, algorithm: str = "sha256") -> HashResult:
        """Calcula o hash de um arquivo e registra o resultado.

        Args:
            file_path: Caminho do arquivo.
            algorithm: Algoritmo de hash (sha256, sha3_512, blake3).

        Returns:
            O HashResult com o resultado do cálculo.
        """
        hash_value = self._compute_hash(file_path, algorithm)
        hash_alg = _ALGORITHM_MAP.get(algorithm, HashAlgorithm.SHA256)

        result = HashResult(
            algorithm=hash_alg,
            hash_value=hash_value,
            file_path=file_path,
            file_size=file_path.stat().st_size if file_path.exists() else None,
        )

        self._session.hash_results.append(result)

        logger.debug("Hash calculado: %s -> %s:%s", file_path.name, algorithm, hash_value[:16])
        return result

    def get_session_data(self) -> dict[str, Any]:
        """Retorna um resumo dos dados da sessão atual.

        Returns:
            Dicionário com estatísticas e dados da sessão.
        """
        evidence_count = len(self._session.evidence_files)
        hash_count = len(self._session.hash_results)

        type_counts: dict[str, int] = {}
        for ev in self._session.evidence_files:
            key = ev.evidence_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        return {
            "session_code": self._session.session_code,
            "case_number": self._session.metadata.case_number,
            "description": self._session.metadata.description,
            "evidence_count": evidence_count,
            "hash_count": hash_count,
            "evidence_by_type": type_counts,
            "created_at": self._session.created_at.isoformat(),
            "updated_at": self._session.updated_at.isoformat(),
        }

    def get_evidence_hashes(self, file_name: str) -> list[HashResult]:
        """Retorna todos os hashes calculados para uma evidência.

        Args:
            file_name: Nome do arquivo de evidência.

        Returns:
            Lista de HashResult para o arquivo.
        """
        return [
            hr
            for hr in self._session.hash_results
            if hr.file_path.name == file_name
        ]

    def verify_integrity(self, file_path: Path) -> bool:
        """Verifica a integridade de um arquivo comparando com o hash original.

        Args:
            file_path: Caminho do arquivo a verificar.

        Returns:
            True se o hash atual confere com o registrado.
        """
        if not file_path.exists():
            logger.warning("Arquivo não encontrado para verificação: %s", file_path)
            return False

        current_hash = self._compute_hash(file_path, "sha256")

        for ev in self._session.evidence_files:
            if ev.file_path == file_path:
                match = current_hash == ev.sha256
                if not match:
                    logger.warning(
                        "Integridade comprometida: %s (esperado %s, obtido %s)",
                        file_path.name,
                        ev.sha256[:16],
                        current_hash[:16],
                    )
                return match

        logger.warning("Evidência não encontrada na sessão: %s", file_path.name)
        return False

    def close_session(self) -> None:
        """Encerra a sessão atual, salvando se houver caminho configurado."""
        if self._session_path is not None and self._is_active:
            self.save_session()

        self._is_active = False
        logger.info("Sessão encerrada: %s", self._session.session_code)

    def _compute_hash(self, file_path: Path, algorithm: str) -> str:
        """Computa o hash de um arquivo delegando para o FileHasher.

        Args:
            file_path: Caminho do arquivo.
            algorithm: Nome do algoritmo de hash.

        Returns:
            Hash em representação hexadecimal.
        """
        return self._hasher.hash_file_str(file_path, algorithm)

    def _compute_all_hashes(self, file_path: Path) -> None:
        """Calcula todos os algoritmos de hash suportados para um arquivo.

        Args:
            file_path: Caminho do arquivo.
        """
        for alg in HASH_ALGORITHMS:
            try:
                self.compute_file_hash(file_path, alg)
            except Exception as e:
                logger.warning("Erro ao calcular %s para %s: %s", alg, file_path.name, e)

    def _rebuild_hash_cache(self) -> None:
        """Reconstrói o cache de hashes a partir dos dados carregados."""
        self._hash_cache.clear()
        for hr in self._session.hash_results:
            name = hr.file_path.name
            if name not in self._hash_cache:
                self._hash_cache[name] = {}
            self._hash_cache[name][hr.algorithm.value] = hr.hash_value
