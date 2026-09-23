"""Script de demonstração do pipeline de preservação do LexProof.

Executa o pipeline completo com dados de demonstração e gera um relatório.
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lexproof.pipeline.preservation import PreservationPipeline, PipelineStepStatus


def progress_callback(step_name: str, status: PipelineStepStatus, progress: float) -> None:
    """Callback para exibir progresso do pipeline."""
    status_icons = {
        PipelineStepStatus.PENDING: "⏳",
        PipelineStepStatus.RUNNING: "🔄",
        PipelineStepStatus.COMPLETED: "✔",
        PipelineStepStatus.FAILED: "❌",
        PipelineStepStatus.SKIPPED: "⏭",
    }

    icon = status_icons.get(status, "?")
    status_text = {
        PipelineStepStatus.PENDING: "pendente",
        PipelineStepStatus.RUNNING: "executando",
        PipelineStepStatus.COMPLETED: "concluído",
        PipelineStepStatus.FAILED: "falhou",
        PipelineStepStatus.SKIPPED: "pulado",
    }

    text = status_text.get(status, status.value)
    print(f"  {icon} {step_name}: {text}")


def main():
    """Executa a demonstração completa do pipeline."""
    print("=" * 60)
    print("LexProof - Demonstração do Pipeline de Preservação")
    print("=" * 60)
    print()

    # Criar imagens de demonstração
    print("1. Criando dados de demonstração...")
    try:
        from demo.create_demo_images import create_demo_screenshot, create_demo_image_with_text
        demo_dir = Path(__file__).parent
        screenshot_path = create_demo_screenshot(demo_dir)
        text_image_path = create_demo_image_with_text(demo_dir)
        print(f"   Imagens criadas em: {demo_dir}")
    except Exception as e:
        print(f"   Aviso: Não foi possível criar imagens: {e}")
        print("   Continuando com apenas o arquivo de texto...")
        screenshot_path = None
        text_image_path = None

    print()

    # Preparar caminhos das evidências
    evidence_paths = []
    whatsapp_path = Path(__file__).parent / "conversa_whatsapp.txt"
    if whatsapp_path.exists():
        evidence_paths.append(whatsapp_path)

    if screenshot_path and screenshot_path.exists():
        evidence_paths.append(screenshot_path)
    if text_image_path and text_image_path.exists():
        evidence_paths.append(text_image_path)

    if not evidence_paths:
        print("Erro: Nenhuma evidência encontrada para processar.")
        return

    print(f"2. Evidências para processar: {len(evidence_paths)}")
    for path in evidence_paths:
        print(f"   - {path.name}")
    print()

    # Criar pipeline
    print("3. Executando pipeline de preservação...")
    print("-" * 40)

    pipeline = PreservationPipeline()
    pipeline.set_progress_callback(progress_callback)

    # Diretório de saída
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Executar pipeline
    result = pipeline.execute(
        evidence_paths=evidence_paths,
        client_name="Cliente de Demonstração",
        case_number="DEMO-2024-001",
        responsible_technician="Técnico de Demonstração",
        output_dir=output_dir,
    )

    print()
    print("=" * 60)
    print("RESUMO DO PROCESSAMENTO")
    print("=" * 60)
    print()

    # Exibir resumo
    print(f"📋 Sessão: {result.session_id}")
    print(f"⏱  Duração total: {result.total_duration_seconds:.2f} segundos")
    print()

    print("📊 Evidências processadas:")
    print(f"   - Total: {result.evidence_count}")
    print(f"   - Imagens: {result.images_count}")
    print(f"   - Exportações: {result.exports_count}")
    print()

    print("🔍 OCR:")
    print(f"   - Imagens processadas: {len(result.ocr_results)}")
    if result.ocr_results:
        for i, ocr in enumerate(result.ocr_results, 1):
            print(f"   - Imagem {i}: {ocr.extracted_text[:50]}...")
    print()

    print("🔐 Hashes calculados:")
    print(f"   - Total: {len(result.hash_results)}")
    for hr in result.hash_results[:4]:  # Mostrar apenas os primeiros
        print(f"   - {hr.algorithm.value}: {hr.hash_value[:32]}...")
    if len(result.hash_results) > 4:
        print(f"   - ... e mais {len(result.hash_results) - 4} hashes")
    print()

    print("📅 Timeline:")
    print(f"   - Entradas: {len(result.timeline)}")
    if result.timeline:
        print(f"   - Período: {result.timeline[0].timestamp} a {result.timeline[-1].timestamp}")
    print()

    print("🔗 Correlação:")
    print(f"   - Correlações encontradas: {len(result.correlations)}")
    for corr in result.correlations:
        print(f"   - {corr.get_summary()}")
    print()

    print("✅ Verificações:")
    print(f"   - Total: {len(result.verification_results)}")
    for vr in result.verification_results:
        status_icon = "✔" if vr.status.value == "pass" else "⚠" if vr.status.value == "warning" else "❌"
        print(f"   - {status_icon} {vr.check_name}: {vr.status.value}")
    print()

    print("🏆 Classificação Técnica:")
    print(f"   - Grau: {result.quality_grade.level.value}")
    print(f"   - Descrição: {result.quality_grade.description}")
    print(f"   - Score: {result.quality_grade.score:.1f}/100")
    if result.quality_grade.recommendations:
        print("   - Recomendações:")
        for rec in result.quality_grade.recommendations:
            print(f"     • {rec}")
    print()

    if result.errors:
        print("❌ Erros:")
        for error in result.errors:
            print(f"   - {error}")
        print()

    if result.warnings:
        print("⚠  Avisos:")
        for warning in result.warnings:
            print(f"   - {warning}")
        print()

    # Relatório
    if result.report_path:
        print(f"📄 Relatório gerado: {result.report_path}")

        # Tentar abrir o relatório
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(result.report_path))
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", str(result.report_path)], check=False)
            else:
                webbrowser.open(f"file://{result.report_path.absolute()}")
            print("   Relatório aberto no navegador!")
        except Exception as e:
            print(f"   Não foi possível abrir automaticamente: {e}")
            print(f"   Abra manualmente: {result.report_path}")
    else:
        print("⚠  Relatório não foi gerado.")

    print()
    print("=" * 60)
    print("Demonstração concluída com sucesso!")
    print("=" * 60)


if __name__ == "__main__":
    main()
