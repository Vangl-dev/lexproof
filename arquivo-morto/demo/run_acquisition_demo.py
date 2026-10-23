"""Demonstração completa da aquisição forense do LexProof."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from demo.create_whatsapp_zip import create_whatsapp_zip
from lexproof.acquisition.acquirer import ForensicAcquirer


def main():
    """Executa a demonstração de aquisição forense."""
    print("=" * 70)
    print("LexProof - Demonstração de Aquisição Forense")
    print("=" * 70)
    print()

    # 1. Criar dados de demonstração
    print("1. Criando dados de demonstração...")
    demo_dir = Path(__file__).parent
    demo_dir.mkdir(exist_ok=True)

    # Criar ZIP do WhatsApp
    zip_path = demo_dir / "conversa_whatsapp_export.zip"
    create_whatsapp_zip(zip_path)
    print(f"   ZIP criado: {zip_path}")

    # Criar imagem avulsa
    from PIL import Image
    img_path = demo_dir / "screenshot_solo.png"
    img = Image.new("RGB", (400, 600), color=(0, 92, 76))
    img.save(img_path)
    print(f"   Imagem criada: {img_path}")

    # Criar TXT avulso
    txt_path = demo_dir / "nota.txt"
    txt_path.write_text("Esta é uma nota de teste para aquisição forense.")
    print(f"   TXT criado: {txt_path}")

    print()

    # 2. Preparar aquisição
    print("2. Preparando aquisição forense...")
    evidence_paths = [zip_path, img_path, txt_path]
    for path in evidence_paths:
        print(f"   - {path.name}")

    print()

    # 3. Executar aquisição
    print("3. Executando aquisição forense...")
    print("-" * 50)

    output_dir = demo_dir / "session_output"
    acquirer = ForensicAcquirer(output_dir)

    results = acquirer.acquire(
        evidence_paths,
        client_name="Cliente de Demonstração",
        case_number="DEMO-2024-001",
        responsible_technician="Técnico de Demonstração",
    )

    print()
    print("=" * 70)
    print("RESUMO DA AQUISIÇÃO")
    print("=" * 70)
    print()

    # 4. Mostrar resultados
    print(f"📁 Diretório de sessão: {output_dir}")
    print()

    print(f"📊 Evidências adquiridas: {len(results)}")
    for i, result in enumerate(results, 1):
        print(f"\n   [{i}] {result.evidence.file_name}")
        print(f"       Tipo: {result.evidence.evidence_type.value}")
        print(f"       Tamanho: {result.evidence.file_size} bytes")
        print(f"       SHA-256: {result.hashes.get('sha256', 'N/A')[:32]}...")
        print(f"       BLAKE3: {result.hashes.get('blake3', 'N/A')[:32]}...")

        if result.zip_manifest:
            print(f"       ZIP Manifest:")
            print(f"         Arquivos: {result.zip_manifest.file_count}")
            for f in result.zip_manifest.files:
                if not f.is_dir:
                    print(f"         - {f.name} ({f.size} bytes)")

    print()

    # 5. Mostrar estrutura da sessão
    print("📁 Estrutura da Sessão:")
    print("-" * 50)

    def show_tree(path: Path, prefix: str = "", is_last: bool = True):
        """Mostra árvore de diretórios."""
        if path.is_dir():
            print(f"{prefix}{'└── ' if is_last else '├── '}{path.name}/")
            children = sorted(path.iterdir())
            for i, child in enumerate(children):
                show_tree(child, prefix + ("    " if is_last else "│   "), i == len(children) - 1)
        else:
            size = path.stat().st_size
            print(f"{prefix}{'└── ' if is_last else '├── '}{path.name} ({size} bytes)")

    show_tree(output_dir)

    print()

    # 6. Mostrar conteúdo dos arquivos de sessão
    print("📄 Arquivos de Sessão:")
    print("-" * 50)

    session_files = [
        "session.json",
        "pipeline.json",
        "zip_manifest.json",
        "hashes.json",
        "metadata.json",
    ]

    for filename in session_files:
        filepath = output_dir / filename
        if filepath.exists():
            print(f"\n📋 {filename}:")
            try:
                data = json.loads(filepath.read_text())
                print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
                if len(json.dumps(data)) > 500:
                    print("   ... (truncado)")
            except Exception as e:
                print(f"   Erro ao ler: {e}")

    print()

    # 7. Verificar integridade
    print("✅ Verificação de Integridade:")
    print("-" * 50)

    for result in results:
        if result.source_path.exists():
            # Recalcular hash
            from lexproof.crypto.hasher import FileHasher
            hasher = FileHasher()
            current_hash = hasher.compute_hash(result.source_path, "sha256")

            if current_hash.hash_value == result.hashes.get("sha256"):
                print(f"   ✔ {result.evidence.file_name}: Integro")
            else:
                print(f"   ❌ {result.evidence.file_name}: MODIFICADO!")
        else:
            print(f"   ⚠ {result.evidence.file_name}: Arquivo não encontrado")

    print()

    # 8. Mostrar pipeline
    print("📋 Pipeline de Processamento:")
    print("-" * 50)

    pipeline_path = output_dir / "pipeline.json"
    if pipeline_path.exists():
        pipeline_data = json.loads(pipeline_path.read_text())
        for step in pipeline_data.get("steps", []):
            print(f"   ✓ {step['step']}: {step['result']}")
            print(f"     Duração: {step['duration_seconds']:.3f}s")

    print()
    print("=" * 70)
    print("Demonstração concluída com sucesso!")
    print("=" * 70)


if __name__ == "__main__":
    main()
