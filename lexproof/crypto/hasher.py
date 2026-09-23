"""Cálculo de hashes de arquivos."""

import hashlib
import logging
from pathlib import Path

from lexproof.models import HashAlgorithm, HashResult

logger = logging.getLogger(__name__)

CHUNK_SIZE = 8192

try:
    import blake3 as _blake3_module
    BLAKE3_AVAILABLE = True
except ImportError:
    BLAKE3_AVAILABLE = False
    _blake3_module = None
    logger.warning("blake3 nao esta instalado. Hash BLAKE3 nao estara disponivel.")


class FileHasher:
    """Calcula hashes de arquivos usando múltiplos algoritmos."""

    @staticmethod
    def _hash_file(file_path: Path, algorithm: HashAlgorithm | str) -> str:
        """Calcula o hash de um arquivo com leitura em chunks.

        Args:
            file_path: Caminho do arquivo.
            algorithm: Algoritmo de hash a utilizar (HashAlgorithm ou str).

        Returns:
            Hash hexadecimal do arquivo.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ValueError: Se o algoritmo não estiver disponível ou for inválido.
        """
        if not file_path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if isinstance(algorithm, str):
            alg_str = algorithm.lower()
            try:
                algorithm = HashAlgorithm(alg_str)
            except ValueError:
                try:
                    hasher = hashlib.new(alg_str)
                except Exception as e:
                    raise ValueError(f"Algoritmo não suportado: {algorithm}") from e

                with open(file_path, "rb") as f:
                    while chunk := f.read(CHUNK_SIZE):
                        hasher.update(chunk)
                return hasher.hexdigest()

        if algorithm == HashAlgorithm.BLAKE3:
            if not BLAKE3_AVAILABLE:
                raise ValueError("Algoritmo BLAKE3 não está disponível. Instale com: pip install blake3")
            hasher = _blake3_module.blake3()
        elif algorithm == HashAlgorithm.SHA256:
            hasher = hashlib.sha256()
        elif algorithm == HashAlgorithm.SHA3_512:
            hasher = hashlib.sha3_512()
        else:
            raise ValueError(f"Algoritmo não suportado: {algorithm}")

        with open(file_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                hasher.update(chunk)

        return hasher.hexdigest()

    @staticmethod
    def hash_file_str(file_path: Path, algorithm: HashAlgorithm | str = HashAlgorithm.SHA256) -> str:
        """Calcula o hash de um arquivo e retorna o valor hexadecimal como string.

        Args:
            file_path: Caminho do arquivo.
            algorithm: Algoritmo de hash (HashAlgorithm ou str).

        Returns:
            Hash hexadecimal do arquivo.
        """
        return FileHasher._hash_file(file_path, algorithm)

    @staticmethod
    def is_blake3_available() -> bool:
        """Verifica se BLAKE3 está disponível."""
        return BLAKE3_AVAILABLE

    def compute_hash(self, file_path: Path, algorithm: HashAlgorithm | str) -> HashResult:
        """Calcula o hash de um arquivo com um algoritmo específico.

        Args:
            file_path: Caminho do arquivo.
            algorithm: Algoritmo de hash (HashAlgorithm ou str).

        Returns:
            Instância de HashResult com o resultado do cálculo.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ValueError: Se o algoritmo não estiver disponível.
        """
        resolved = file_path.resolve()
        hash_value = self._hash_file(resolved, algorithm)
        file_size = resolved.stat().st_size

        if isinstance(algorithm, str):
            try:
                hash_alg = HashAlgorithm(algorithm.lower())
            except ValueError:
                hash_alg = HashAlgorithm.SHA256
        else:
            hash_alg = algorithm

        return HashResult(
            file_path=resolved,
            algorithm=hash_alg,
            hash_value=hash_value,
            file_size=file_size,
        )

    def compute_all_hashes(self, file_path: Path) -> list[HashResult]:
        """Calcula hashes de um arquivo com todos os algoritmos suportados.

        Args:
            file_path: Caminho do arquivo.

        Returns:
            Lista de HashResult, um para cada algoritmo disponível.
        """
        results = []
        for algorithm in HashAlgorithm:
            if algorithm == HashAlgorithm.BLAKE3 and not BLAKE3_AVAILABLE:
                logger.debug("BLAKE3 indisponivel, ignorando para %s", file_path.name)
                continue
            try:
                results.append(self.compute_hash(file_path, algorithm))
            except Exception as e:
                logger.warning("Erro ao calcular %s para %s: %s", algorithm.value, file_path.name, e)
        return results

    @staticmethod
    def compute_merkle_root(hashes: list[str]) -> str:
        """Calcula a raiz de Merkle a partir de uma lista de hashes."""
        if not hashes:
            return ""
        if len(hashes) == 1:
            return hashes[0]

        level = list(hashes)
        while len(level) > 1:
            next_level: list[str] = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                combined = hashlib.sha256(
                    (left + right).encode("utf-8")
                ).hexdigest()
                next_level.append(combined)
            level = next_level

        return level[0]

    def compute_global_hash(self, file_paths: list[Path]) -> str:
        """Calcula um hash global de múltiplos arquivos."""
        individual_hashes: list[str] = []
        for fp in file_paths:
            result = self.compute_hash(fp, HashAlgorithm.SHA256)
            individual_hashes.append(result.hash_value)
        return self.compute_merkle_root(individual_hashes)
