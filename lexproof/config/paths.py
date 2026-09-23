"""Gerenciamento de caminhos do LexProof."""

from pathlib import Path

from lexproof.core.constants import SESSION_FILE_EXTENSION


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
    def cases_dir(cls) -> Path:
        """Diretório raiz de todos os casos (~/.lexproof/cases)."""
        path = cls.config_dir() / "cases"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def case_dir(cls, session_code: str) -> Path:
        """Diretório permanente de um caso específico.

        Args:
            session_code: Código amigável da sessão (ex.: LEX-Ab12Cd34).

        Returns:
            Caminho do diretório do caso (criado se não existir).
        """
        safe_code = session_code.replace("/", "_").replace("\\", "_").strip()
        if not safe_code:
            raise ValueError("session_code não pode ser vazio")
        path = cls.cases_dir() / safe_code
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def session_file_path(cls, session_code: str) -> Path:
        """Caminho completo do arquivo de sessão de um caso.

        Layout: ~/.lexproof/cases/<session_code>/case.lexproof.json
        """
        return cls.case_dir(session_code) / f"case{SESSION_FILE_EXTENSION}"

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
