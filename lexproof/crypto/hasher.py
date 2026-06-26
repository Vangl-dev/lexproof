"""Cálculo de hashes de arquivos."""

import hashlib
from pathlib import Path

import blake3

from lexproof.models import HashAlgorithm, HashResult

CHUNK_SIZE = 8192


class FileHasher:
    """Calcula hashes de arquivos usando múltiplos algoritmos."""

    @staticmethod
    def _hash_file(file_path: Path, algorithm: HashAlgorithm) -> str:
        """Calcula o hash de um arquivo com leitura em chunks.

        Args:
            file_path: Caminho do arquivo.
            algorithm: Algoritmo de hash a utilizar.

        Returns:
            Hash hexadecimal do arquivo.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
        """
        if not file_path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        if algorithm == HashAlgorithm.BLAKE3:
            hasher = blake3.blake3()
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

    def compute_hash(self, file_path: Path, algorithm: HashAlgorithm) -> HashResult:
        """Calcula o hash de um arquivo com um algoritmo específico.

        Args:
            file_path: Caminho do arquivo.
            algorithm: Algoritmo de hash.

        Returns:
            Instância de HashResult com o resultado do cálculo.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
        """
        resolved = file_path.resolve()
        hash_value = self._hash_file(resolved, algorithm)
        file_size = resolved.stat().st_size
        return HashResult(
            file_path=resolved,
            algorithm=algorithm,
            hash_value=hash_value,
            file_size=file_size,
        )

    def compute_all_hashes(self, file_path: Path) -> list[HashResult]:
        """Calcula hashes de um arquivo com todos os algoritmos suportados.

        Args:
            file_path: Caminho do arquivo.

        Returns:
            Lista de HashResult, um para cada algoritmo.
        """
        results = []
        for algorithm in HashAlgorithm:
            results.append(self.compute_hash(file_path, algorithm))
        return results

    @staticmethod
    def compute_merkle_root(hashes: list[str]) -> str:
        """Calcula a raiz de Merkle a partir de uma lista de hashes.

        Se a lista tiver um único elemento, retorna esse hash.
        Caso contrário, combina pares recursivamente com SHA256 até
        restar um único hash (raiz).

        Args:
            hashes: Lista de strings hexadecimais de hash.

        Returns:
            Hash hexadecimal da raiz de Merkle.
        """
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
        """Calcula um hash global de múltiplos arquivos.

        Para cada arquivo, calcula o hash SHA256, depois combina todos
        em uma raiz de Merkle.

        Args:
            file_paths: Lista de caminhos dos arquivos.

        Returns:
            Hash hexadecimal da raiz de Merkle (hash global).
        """
        individual_hashes: list[str] = []
        for fp in file_paths:
            result = self.compute_hash(fp, HashAlgorithm.SHA256)
            individual_hashes.append(result.hash_value)
        return self.compute_merkle_root(individual_hashes)
