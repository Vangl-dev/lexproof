"""Script para criar imagens de demonstração do LexProof."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_demo_screenshot(output_dir: Path) -> Path:
    """Cria um screenshot simulado de conversa WhatsApp."""
    # Criar imagem
    width, height = 400, 600
    img = Image.new("RGB", (width, height), color=(0, 92, 76))  # Verde WhatsApp
    draw = ImageDraw.Draw(img)

    # Tentar usar fonte padrão
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font

    # Cabeçalho
    draw.rectangle([(0, 0), (width, 60)], fill=(0, 100, 80))
    draw.text((20, 20), "Conversa com Maria", fill="white", font=font)

    # Mensagens
    messages = [
        ("João", "Bom dia!", (255, 255, 255), (200, 230, 200)),
        ("Maria", "Oi João, tudo bem?", (0, 0, 0), (255, 255, 255)),
        ("João", "Tudo ótimo!", (255, 255, 255), (200, 230, 200)),
        ("Maria", "Claro, o que precisa?", (0, 0, 0), (255, 255, 255)),
        ("João", "Preciso do documento", (255, 255, 255), (200, 230, 200)),
    ]

    y = 80
    for sender, text, text_color, bg_color in messages:
        # Balão de mensagem
        if sender == "João":
            x = width - 250
            draw.rounded_rectangle(
                [(x, y), (width - 10, y + 40)],
                radius=10,
                fill=bg_color,
            )
        else:
            x = 10
            draw.rounded_rectangle(
                [(x, y), (x + 240, y + 40)],
                radius=10,
                fill=bg_color,
            )

        # Texto
        draw.text((x + 10, y + 5), f"{sender}: {text}", fill=text_color, font=font_small)
        y += 60

    # Salvar
    output_path = output_dir / "screenshot_conversa.png"
    img.save(output_path)
    return output_path


def create_demo_image_with_text(output_dir: Path) -> Path:
    """Cria uma imagem com texto visível para OCR."""
    width, height = 500, 300
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Texto para OCR
    lines = [
        "15/03/2024 10:00, João: Bom dia!",
        "15/03/2024 10:01, Maria: Olá!",
        "15/03/2024 10:02, João: Tudo bem?",
        "15/03/2024 10:03, Maria: Sim, e você?",
    ]

    y = 20
    for line in lines:
        draw.text((20, y), line, fill="black", font=font)
        y += 30

    # Salvar
    output_path = output_dir / "documento_texto.png"
    img.save(output_path)
    return output_path


def main():
    """Cria todas as imagens de demonstração."""
    demo_dir = Path(__file__).parent
    demo_dir.mkdir(exist_ok=True)

    print("Criando imagens de demonstração...")

    # Criar screenshot
    screenshot_path = create_demo_screenshot(demo_dir)
    print(f"Screenshot criado: {screenshot_path}")

    # Criar imagem com texto
    text_image_path = create_demo_image_with_text(demo_dir)
    print(f"Imagem com texto criada: {text_image_path}")

    print("Imagens de demonstração criadas com sucesso!")


if __name__ == "__main__":
    main()
