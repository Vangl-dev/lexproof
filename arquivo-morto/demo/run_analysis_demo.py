"""Demonstração do Smart Analysis Engine."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lexproof.analysis.engine import SmartAnalysisEngine
from lexproof.analysis.models import EvidenceAnalysis, FindingSeverity
from lexproof.models.evidence import (
    ChatExportEvidence,
    Evidence,
    EvidenceType,
    ImageEvidence,
)
from lexproof.models.message import MessageType, WhatsAppMessage


def create_demo_data() -> tuple[list[Evidence], list[WhatsAppMessage]]:
    """Cria dados de demonstração."""
    demo_dir = Path(__file__).parent

    evidences = []
    messages = []

    # Criar exportação WhatsApp
    chat_path = demo_dir / "conversa_whatsapp.txt"
    if chat_path.exists():
        chat_evidence = ChatExportEvidence(
            file_path=chat_path,
            file_name=chat_path.name,
            file_size=chat_path.stat().st_size,
            evidence_type=EvidenceType.CHAT_EXPORT,
            sha256="abc123",
            blake3="def456",
            export_format="whatsapp",
            message_count=25,
            participant_count=2,
            participants=["João", "Maria"],
        )
        evidences.append(chat_evidence)

    # Criar imagens de teste
    for i in range(5):
        img_path = demo_dir / f"img_{i}.png"
        if img_path.exists():
            img_evidence = ImageEvidence(
                file_path=img_path,
                file_name=img_path.name,
                file_size=img_path.stat().st_size,
                evidence_type=EvidenceType.IMAGE,
                sha256=f"hash_{i}",
                blake3=f"blake_{i}",
                width=400,
                height=600,
                format="PNG",
            )
            evidences.append(img_evidence)

    # Criar mensagens de demonstração
    base_time = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)

    demo_messages = [
        ("João", "Bom dia!"),
        ("Maria", "Oi João, tudo bem?"),
        ("João", "Tudo ótimo! Preciso de uma ajuda."),
        ("Maria", "Claro, o que precisa?"),
        ("João", "Preciso do documento que você me mandou ontem."),
        # Lacuna de 45 minutos
        ("Maria", "Ah, sim! Vou procurar aqui."),
        ("Maria", "<Mídia ocultada>"),
        ("João", "Recebi, obrigado!"),
        ("Maria", "De nada! Qualquer coisa é só chamar."),
        ("João", "Pretende ir ao evento de sábado?"),
        # Mensagem interrompida
        ("Maria", "Ainda não"),
        ("Maria", "decidi. Depende do horário."),
        ("João", "O evento começa às 14h no centro."),
        ("Maria", "Ah, legal! Vou tentar ir."),
        ("João", "Perfeito! Vou te esperar lá."),
    ]

    current_time = base_time
    for i, (sender, content) in enumerate(demo_messages):
        # Adicionar lacuna após a mensagem 4
        if i == 5:
            current_time += timedelta(minutes=45)

        msg = WhatsAppMessage(
            line_number=i + 1,
            timestamp=current_time,
            sender=sender,
            content=content,
        )
        messages.append(msg)
        current_time += timedelta(minutes=1)

    return evidences, messages


def main():
    """Executa a demonstração do Smart Analysis Engine."""
    print("=" * 70)
    print("LexProof - Smart Analysis Engine Demo")
    print("=" * 70)
    print()

    # Criar dados
    print("1. Criando dados de demonstração...")
    evidences, messages = create_demo_data()
    print(f"   {len(evidences)} evidências")
    print(f"   {len(messages)} mensagens")
    print()

    # Executar análise
    print("2. Executando análise...")
    print("-" * 50)

    engine = SmartAnalysisEngine()
    analysis = engine.analyze(evidences, messages)

    print()
    print("=" * 70)
    print("RESULTADO DA ANÁLISE")
    print("=" * 70)
    print()

    # Plataforma detectada
    print(f"📱 Plataforma: {analysis.detected_platform}")
    print()

    # Resumo Executivo
    print("📋 RESUMO EXECUTIVO")
    print("-" * 50)
    print(analysis.generate_executive_summary_text())
    print()

    # Scores Técnicos
    print("📊 SCORES TÉCNICOS")
    print("-" * 50)
    scores = analysis.scores.to_dict()
    for key, value in scores.items():
        if key != "technical_grade":
            print(f"   {key.replace('_', ' ').title()}: {value}%")
    print(f"\n   🏆 Grau Técnico: {scores['technical_grade']}")
    print()

    # Saúde do Conjunto
    print("💚 SAÚDE DO CONJUNTO")
    print("-" * 50)
    health = analysis.health.to_dict()
    print(f"   Score Geral: {health['overall_score']}%")
    print(f"   Integridade: {health['integrity_status']}")
    print(f"   Timeline: {health['timeline_status']}")
    print(f"   OCR: {health['ocr_status']}")
    print(f"   Correlação: {health['correlation_status']}")
    print(f"   Metadados: {health['metadata_status']}")
    print(f"   Lacunas: {health['gaps_count']}")
    print(f"   Duplicidades: {health['duplicates_count']}")
    print()

    # Constatações
    print("🔍 CONSTATAÇÕES")
    print("-" * 50)
    for finding in analysis.findings:
        severity_icon = {
            FindingSeverity.INFO: "ℹ️",
            FindingSeverity.WARNING: "⚠️",
            FindingSeverity.ERROR: "❌",
            FindingSeverity.SUCCESS: "✅",
        }.get(finding.severity, "•")

        print(f"   {severity_icon} [{finding.category.value}] {finding.title}")
        print(f"      {finding.description}")
        print(f"      Confiança: {finding.confidence:.0%}")
        if finding.recommendation:
            print(f"      Recomendação: {finding.recommendation}")
        print()

    # Recomendações
    print("💡 RECOMENDAÇÕES")
    print("-" * 50)
    for i, rec in enumerate(analysis.recommendations, 1):
        print(f"   {i}. {rec}")
    print()

    # Limitações
    print("⚠️ LIMITAÇÕES")
    print("-" * 50)
    print(analysis.generate_limitations_text())
    print()

    # Logs de Decisão (últimos 5)
    print("📝 LOGS DE DECISÃO (últimos 5)")
    print("-" * 50)
    for log in analysis.decision_logs[-5:]:
        print(f"   • {log.rule}")
        print(f"     Dados: {log.data_analyzed}")
        print(f"     Justificativa: {log.justification}")
        print()

    # Salvar análise completa
    output_path = Path(__file__).parent / "analysis_result.json"
    output_path.write_text(
        json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"📄 Análise completa salva em: {output_path}")

    print()
    print("=" * 70)
    print("Demonstração concluída!")
    print("=" * 70)


if __name__ == "__main__":
    main()
