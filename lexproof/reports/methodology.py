"""Gerador de metodologia para relatórios do LexProof.

Documenta os procedimentos técnicos executados durante a preservação,
garantindo transparência e reprodutibilidade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class MethodologyStep:
    """Um passo da metodologia executada."""

    name: str
    description: str
    timestamp: datetime
    details: Optional[str] = None
    duration_seconds: Optional[float] = None


class MethodologyGenerator:
    """Gerador de documentação de metodologia.

    Cria a seção de metodologia do relatório, documentando
    cada procedimento técnico executado durante a preservação.
    """

    def __init__(self) -> None:
        """Inicializa o gerador de metodologia."""
        self._steps: list[MethodologyStep] = []
        self._start_time: Optional[datetime] = None

    def start(self) -> None:
        """Marca o início da preservação."""
        self._start_time = datetime.now(timezone.utc)
        self._steps = []

    def add_step(
        self,
        name: str,
        description: str,
        details: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Adiciona um passo à metodologia.

        Args:
            name: Nome do passo.
            description: Descrição do que foi feito.
            details: Detalhes adicionais (opcional).
            duration_seconds: Duração em segundos (opcional).
        """
        step = MethodologyStep(
            name=name,
            description=description,
            timestamp=datetime.now(timezone.utc),
            details=details,
            duration_seconds=duration_seconds,
        )
        self._steps.append(step)

    def generate_methodology_section(self) -> str:
        """Gera a seção de metodologia completa para o relatório.

        Returns:
            Texto formatado da metodologia.
        """
        if not self._steps:
            return self._get_empty_methodology()

        lines = []

        # Cabeçalho
        lines.append("# Metodologia")
        lines.append("")
        lines.append(
            "Esta seção documenta os procedimentos técnicos executados "
            "durante a preservação das evidências digitais."
        )
        lines.append("")
        lines.append(
            "A metodologia é reproduzível e transparente, permitindo "
            "que qualquer pessoa com conhecimento técnico possa reproduzir "
            "os mesmos procedimentos."
        )
        lines.append("")

        # Fluxo visual
        lines.append("## Fluxo de Execução")
        lines.append("")
        lines.append("```")
        for i, step in enumerate(self._steps):
            if i > 0:
                lines.append("↓")
            lines.append(step.name)
        lines.append("```")
        lines.append("")

        # Detalhes de cada passo
        lines.append("## Detalhamento dos Procedimentos")
        lines.append("")

        for i, step in enumerate(self._steps, 1):
            lines.append(f"### {i}. {step.name}")
            lines.append("")
            lines.append(f"**Descrição:** {step.description}")
            lines.append("")

            if step.details:
                lines.append("**Detalhes:**")
                lines.append(step.details)
                lines.append("")

            if step.duration_seconds is not None:
                minutes = int(step.duration_seconds // 60)
                seconds = int(step.duration_seconds % 60)
                if minutes > 0:
                    duration_str = f"{minutes} minuto(s) e {seconds} segundo(s)"
                else:
                    duration_str = f"{seconds} segundo(s)"
                lines.append(f"**Duração:** {duration_str}")
                lines.append("")

            lines.append(
                f"**Data/Hora:** {step.timestamp.strftime('%d/%m/%Y %H:%M:%S UTC')}"
            )
            lines.append("")
            lines.append("---")
            lines.append("")

        # Resumo temporal
        if self._start_time:
            end_time = datetime.now(timezone.utc)
            total_duration = (end_time - self._start_time).total_seconds()
            minutes = int(total_duration // 60)
            seconds = int(total_duration % 60)

            lines.append("## Resumo Temporal")
            lines.append("")
            lines.append(f"**Início:** {self._start_time.strftime('%d/%m/%Y %H:%M:%S UTC')}")
            lines.append(f"**Fim:** {end_time.strftime('%d/%m/%Y %H:%M:%S UTC')}")
            if minutes > 0:
                lines.append(f"**Duração Total:** {minutes} minuto(s) e {seconds} segundo(s)")
            else:
                lines.append(f"**Duração Total:** {seconds} segundo(s)")
            lines.append("")

        # Nota sobre transparência
        lines.append("## Nota sobre Transparência")
        lines.append("")
        lines.append(
            "Todos os procedimentos acima foram executados de forma automática "
            "pelo sistema LexProof. Os resultados são determinísticos para os "
            "mesmos dados de entrada, garantindo reprodutibilidade."
        )
        lines.append("")
        lines.append(
            "Ausência de metadados em imagens é compatível com plataformas "
            "que removem informações durante upload ou compartilhamento. "
            "Tal ausência não deve ser tratada como indício de fraude."
        )
        lines.append("")

        return "\n".join(lines)

    def _get_empty_methodology(self) -> str:
        """Retorna metodologia vazia quando nenhum passo foi registrado."""
        return (
            "# Metodologia\n\n"
            "Nenhum procedimento foi documentado.\n"
        )

    def generate_methodology_summary(self) -> str:
        """Gera um resumo curto da metodologia.

        Returns:
            Resumo formatado.
        """
        if not self._steps:
            return "Metodologia não documentada"

        step_names = [step.name for step in self._steps]
        return " → ".join(step_names)
