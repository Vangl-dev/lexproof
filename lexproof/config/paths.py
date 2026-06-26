"""Gerenciamento de caminhos do LexProof."""

from pathlib import Path


class Paths:
    """Centraliza e garante a existência de todos os diretórios da aplicação."""

    _APP_ROOT: Path = Path(__file__).resolve().parent.parent

    @classmethod
    def app_dir(cls) -> Path:
        """Diretório raiz do pacote lexproof."""
        return cls._APP_ROOT

    @classmethod
    def config_dir(cls) -> Path:
        """Diretório de configurações do usuário (~/.lexproof)."""
        path = Path.home() / ".lexproof"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def log_dir(cls) -> Path:
        """Diretório de logs."""
        path = cls.config_dir() / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def temp_dir(cls) -> Path:
        """Diretório temporário."""
        path = cls.config_dir() / "temp"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def output_dir(cls) -> Path:
        """Diretório de saída (relatórios, manifestos, etc.)."""
        path = cls.config_dir() / "output"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def resources_dir(cls) -> Path:
        """Diretório de recursos estáticos (templates, dados)."""
        path = cls._APP_ROOT / "resources"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def icons_dir(cls) -> Path:
        """Diretório de ícones da interface."""
        path = cls.resources_dir() / "icons"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def relative_to_app(cls, path: Path) -> Path:
        """Retorna um caminho relativo ao diretório raiz do app.

        Args:
            path: Caminho absoluto ou relativo a ser convertido.

        Returns:
            Caminho relativo ao diretório do app.
        """
        try:
            return path.resolve().relative_to(cls._APP_ROOT.resolve())
        except ValueError:
            return path
