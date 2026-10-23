"""Script para criar um ZIP de demonstração do WhatsApp."""

import zipfile
from pathlib import Path


def create_whatsapp_zip(output_path: Path) -> Path:
    """Cria um ZIP simulando exportação do WhatsApp.

    Args:
        output_path: Caminho do arquivo ZIP de saída.

    Returns:
        Caminho do ZIP criado.
    """
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Adicionar _chat.txt (padrão WhatsApp)
        chat_content = """\
Mensagens e chamadas são criptografadas de ponta a ponta. Ninguém fora desta conversa pode ler ou escutá-las.

15/03/2024 10:00, João: Bom dia, pessoal!
15/03/2024 10:01, Maria: Oi João, tudo bem?
15/03/2024 10:02, João: Tudo ótimo! Preciso de uma ajuda.
15/03/2024 10:03, Maria: Claro, o que precisa?
15/03/2024 10:05, João: Preciso do documento que você me mandou ontem.
15/03/2024 10:06, Maria: Ah, sim! Vou procurar aqui.
15/03/2024 10:10, Maria: <Mídia ocultada>
15/03/2024 10:15, João: Recebi, obrigado!
15/03/2024 10:20, Maria: De nada! Qualquer coisa é só chamar.
15/03/2024 10:25, João: Pretende ir ao evento de sábado?
15/03/2024 10:30, Maria: Ainda não decidi. Depende do horário.
15/03/2024 10:35, João: O evento começa às 14h no centro.
15/03/2024 10:40, Maria: Ah, legal! Vou tentar ir.
15/03/2024 10:45, João: Perfeito! Vou te esperar lá.
15/03/2024 10:50, Maria: Combinado! Até lá.
"""
        zf.writestr("_chat.txt", chat_content)

        # Adicionar imagens simuladas
        from PIL import Image
        import io

        # Criar imagem 1
        img1 = Image.new("RGB", (400, 600), color=(0, 92, 76))
        buf1 = io.BytesIO()
        img1.save(buf1, format="JPEG")
        zf.writestr("IMG-20240315-WA0001.jpg", buf1.getvalue())

        # Criar imagem 2
        img2 = Image.new("RGB", (500, 300), color="white")
        buf2 = io.BytesIO()
        img2.save(buf2, format="PNG")
        zf.writestr("IMG-20240315-WA0002.png", buf2.getvalue())

        # Criar pasta de mídia
        zf.writestr("media/", "")

    return output_path


def main():
    """Cria o ZIP de demonstração."""
    demo_dir = Path(__file__).parent
    output_path = demo_dir / "conversa_whatsapp_export.zip"

    print("Criando ZIP de demonstração do WhatsApp...")
    create_whatsapp_zip(output_path)
    print(f"ZIP criado: {output_path}")

    # Mostrar conteúdo
    with zipfile.ZipFile(output_path, "r") as zf:
        print(f"\nConteúdo do ZIP:")
        for info in zf.infolist():
            if not info.is_dir():
                print(f"  - {info.filename} ({info.file_size} bytes)")


if __name__ == "__main__":
    main()
