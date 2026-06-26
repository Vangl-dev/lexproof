# LexProof

**Sistema de Preservação Técnica de Evidências Digitais**

[![Versão](https://img.shields.io/badge/versão-0.1.0--beta-blue)](https://github.com/lexproof/lexproof)
[![Licença](https://img.shields.io/badge/licença-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13+-yellow)](https://www.python.org/)

LexProof é uma aplicação desktop profissional projetada para o mercado jurídico brasileiro, fornecendo ferramentas completas para preservação, verificação e apresentação de evidências digitais em processos legais.

---

## Funcionalidades

### Preservação de Evidências
- Importação multi-formato (imagens, PDFs, texto, arquivos compactados, vídeos)
- Detecção automática do tipo de evidência
- Cálculo de hash SHA-256 na importação
- Rastreamento completo de metadados

### Integridade Criptográfica
- Hashing multi-algoritmo: SHA-256, SHA3-512, BLAKE3
- Árvore Merkle para cálculo de hash global
- Geração de manifestos versionados em JSON
- Verificação de integridade contra hashs originais

### Cadeia de Custódia
- Criação automática na importação de evidências
- Tipos de evento: IMPORTAÇÃO, HASH, VERIFICAÇÃO, EXPORTAÇÃO, MODIFICAÇÃO, ANOTAÇÃO
- Rastreamento de hash antes/depois para cada evento
- Registro de operador e metadados

### Parser de Conversas do WhatsApp
- Parsing de arquivos `.txt` exportados do WhatsApp
- Detecção automática de formatos de data (brasileiro e internacional)
- Classificação de mensagens: TEXTO, MÍDIA, DELETADA, EDITADA, SISTEMA, STICKER, ÁUDIO, VÍDEO, LINK
- Extração de remetente e referências de mídia

### OCR (Reconhecimento Óptico de Caracteres)
- Dois motores: Tesseract e EasyOCR (configuráveis)
- Pipeline de pré-processamento de imagens
- Extração de texto com caixas delimitadoras e escores de confiança
- Detecção de timestamps e remetentes no texto OCR
- Comparação OCR vs TXT para validação cruzada

### Processamento de PDFs e Imagens
- Extração de texto e metadados de PDFs
- Extração de metadados EXIF de imagens
- Suporte a múltiplos formatos: PNG, JPG, GIF, BMP, TIFF, WebP, HEIC

### Timeline Forense
- Consolidação de múltiplas fontes (TXT + OCR)
- Ordenação cronológica com detecção de duplicatas
- Detecção de lacunas temporais configuráveis
- Comparação de timelines com escore de similaridade ponderado

### Sistema de Verificação (7 verificações)
1. OCR vs TXT - Consistência entre OCR e texto
2. Verificação de timestamps - Duplicatas, ordem, anos suspeitos
3. Verificação de remetentes - Anomalias e comprimentos
4. Ordem de mensagens - Validação cronológica
5. Contagem de mensagens - Validação com distribuição por tipo
6. Integridade de arquivos - Recálculo SHA-256
7. Verificação EXIF - Presença de metadados e consistência de datas

### Geração de Relatórios
- Relatórios HTML responsivos com temas claro/escuro
- Relatórios PDF profissionais com capa e sumário
- Códigos QR para verificação externa
- Seções configuráveis e notas personalizadas

### Ancoragem Blockchain (Opcional)
- OpenTimestamps - Timestamping descentralizado ancorado no Bitcoin
- RFC3161 - Timestamping baseado em TSA
- Arquitetura plugável com degradação graciosa

### Interface Gráfica Desktop
- Janela principal com barra lateral, sistema de abas e painel de log
- Barra lateral recolhível com seções animadas
- Drag-and-drop com overlay animado
- Painel de log filtrável e exportável
- Barra de status com barra de progresso
- Temas: Claro, Escuro e Sistema (auto-detecção)
- Atalhos de teclado (Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+I, Ctrl+B, Ctrl+L, Ctrl+Q)

---

## Instalação

### Pré-requisitos
- Python 3.13 ou superior
- pip
- Tesseract OCR (opcional, para funcionalidade OCR)

### Instalação via pip

```bash
pip install lexproof
```

### Instalação para desenvolvimento

```bash
git clone https://github.com/lexproof/lexproof.git
cd lexproof
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

### Instalando Tesseract OCR (Linux)

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

### Instalando Tesseract OCR (macOS)

```bash
brew install tesseract
```

---

## Uso

### Iniciando a aplicação

```bash
python -m lexproof
```

### Fluxo de trabalho básico

1. **Criar um novo caso**: Arquivo → Novo Caso (Ctrl+N)
2. **Importar evidências**: Arraste arquivos para a janela ou use Arquivo → Importar (Ctrl+I)
3. **Analisar**: As evidências são automaticamente hasheadas e adicionadas à cadeia de custódia
4. **Verificar**: Use as ferramentas de verificação para validar a integridade
5. **Gerar relatório**: Exporte relatórios em HTML ou PDF

### Configuração

As configurações são salvas em `~/.lexproof/settings.json` e podem ser alteradas via Editar → Preferências.

Variáveis de ambiente (prefixo `LEXPROOF_`):
- `LEXPROOF_THEME`: Tema da interface (light/dark/system)
- `LEXPROOF_LANGUAGE`: Idioma (pt_BR)
- `LEXPROOF_OCR_ENGINE`: Motor OCR (tesseract/easyocr)
- `LEXPROOF_OUTPUT_DIR`: Diretório de saída para relatórios

---

## Capturas de Tela

> *Em breve*

---

## Estrutura do Projeto

```
lexproof/
├── core/           # Framework principal da aplicação
├── config/         # Configuração e gerenciamento de caminhos
├── models/         # Modelos de dados Pydantic
├── crypto/         # Operações criptográficas e manifestos
├── blockchain/     # Ancoragem blockchain (opcional)
├── ocr/            # Integração com motores OCR
├── parsers/        # Parsers de formatos de arquivo
├── reports/        # Geração de relatórios HTML e PDF
├── timeline/       # Análise forense de timeline
├── verification/   # Sistema de verificação de evidências
├── ui/             # Interface gráfica PySide6
└── utils/          # Funções utilitárias
```

---

## Desenvolvimento

### Configuração do ambiente

```bash
pip install -e ".[dev]"
pre-commit install
```

### Comandos úteis

```bash
# Linting
ruff check lexproof/
ruff format lexproof/

# Type checking
mypy lexproof/

# Testes
pytest
pytest --cov=lexproof
pytest --cov=lexproof --cov-report=html
```

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.13 |
| GUI | PySide6 (Qt6) |
| Modelos | Pydantic v2 |
| Build | Hatchling |
| Hashing | hashlib + blake3 |
| OCR | pytesseract + EasyOCR |
| Processamento de Imagens | Pillow + NumPy |
| Geração de PDF | ReportLab |
| Templates HTML | Jinja2 |
| QR Codes | qrcode |
| Blockchain | opentimestamps + pyopenssl |

---

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## Contribuindo

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para informações sobre como contribuir com o projeto.

---

## Segurança

Consulte [SECURITY.md](SECURITY.md) para informações sobre a política de segurança e reporte de vulnerabilidades.

---

## Roadmap

Consulte [ROADMAP.md](ROADMAP.md) para ver o plano de desenvolvimento e funcionalidades futuras.

---

*Desenvolvido com dedicação para o mercado jurídico brasileiro.*
