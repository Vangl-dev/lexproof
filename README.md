# LexProof

**Sistema de Preservação Técnica de Evidências Digitais**

[![Versão](https://img.shields.io/badge/versão-0.43--beta-blue)](https://github.com/lexproof/lexproof)
[![Licença](https://img.shields.io/badge/licença-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-yellow)](https://www.python.org/)

LexProof é uma aplicação desktop profissional projetada para o mercado jurídico brasileiro, fornecendo ferramentas completas para preservação, verificação e apresentação de evidências digitais em processos legais.

---

## Objetivo

Permitir que um advogado consiga preservar conversas digitais hoje e demonstrar, meses ou anos depois, exatamente qual era o estado dessas evidências quando foram submetidas ao sistema.

---

## Fluxo Principal

1. **Nova Preservação** → Criar uma nova sessão de trabalho
2. **Importar ZIP** → Selecionar arquivo exportado do WhatsApp
3. **Processamento Automático** → Pipeline executa todas as etapas
4. **Diagnóstico** → Smart Analysis gera relatório técnico
5. **Relatório PDF** → Documento profissional é gerado e aberto automaticamente

---

## Funcionalidades

### Preservação Automática
- Importação de ZIPs exportados do WhatsApp
- Detecção automática de tipo de evidência
- Processamento completo sem intervenção manual

### Pipeline de Processamento
- **Catalogação** → Organização dos arquivos
- **Metadados** → Extração de informações dos arquivos
- **Hashes** → Cálculo de assinaturas digitais (SHA-256)
- **OCR** → Leitura de texto das imagens
- **Parser** → Leitura da conversa do WhatsApp
- **Correlação** → Combinação de prints com a conversa
- **Timeline** → Reconstrução da ordem das mensagens
- **Verificação** → Conferência de integridade
- **Relatório** → Montagem do documento profissional

### Interface Visual
- Pipeline com barra de progresso e porcentagem
- Descrições humanas para cada etapa
- Tempo de execução por etapa
- Tela de resumo ao finalizar
- Análise imediata do ZIP (arquivos, imagens, WhatsApp)

### Relatório Profissional
- PDF com capa, sumário e seções detalhadas
- Hashes de integridade com códigos visuais
- Cadeia de custódia documentada
- Resultados de verificação
- Abertura automática do relatório

---

## Instalação

### Pré-requisitos
- Python 3.10 ou superior
- pip

### Instalação para desenvolvimento

```bash
git clone https://github.com/lexproof/lexproof.git
cd lexproof
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -e ".[dev]"
```

### Dependências Opcionais

```bash
# BLAKE3 (hash adicional)
pip install blake3

# Tesseract OCR (leitura de imagens)
sudo apt-get install tesseract-ocr tesseract-ocr-por  # Linux
brew install tesseract  # macOS
```

---

## Uso

### Iniciando a aplicação

```bash
python -m lexproof
```

### Fluxo de Trabalho

1. Clique em **"Importar Evidências"** ou arraste um ZIP para a janela
2. Selecione o arquivo ZIP exportado do WhatsApp
3. Acompanhe o processamento na aba Pipeline
4. Ao finalizar, o relatório PDF será aberto automaticamente
5. Visualize o diagnóstico na aba Timeline ou Hashes

---

## Primeiro Caso Real

Após as sprints v0.41-v0.43, o LexProof atingiu o estágio de **primeiro caso real**:

- **Integração completa** de todos os módulos
- **Interface funcional** com fluxo do usuário
- **Tratamento de erros** sem travamentos
- **Experiência visual** com progresso em tempo real
- **Relatório PDF** gerado e aberto automaticamente

Veja [FIRST_REAL_CASE.md](FIRST_REAL_CASE.md) para detalhes do primeiro teste.

---

## Estrutura do Projeto

```
lexproof/
├── core/           # Framework principal (EventBus, Session)
├── config/         # Configuração e caminhos
├── models/         # Modelos de dados Pydantic
├── crypto/         # Hashing (SHA-256, BLAKE3)
├── ocr/            # Reconhecimento de caracteres
├── parsers/        # Parsers de formatos
├── reports/        # Geração de relatórios PDF/HTML
├── timeline/       # Análise forense de timeline
├── verification/   # Sistema de verificação
├── correlation/    # Correlacionador print × exportação
├── analysis/       # Smart Analysis Engine
├── acquisition/    # Aquisição forense de ZIPs
├── pipeline/       # Pipeline de preservação
└── ui/             # Interface gráfica PySide6
```

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.10+ |
| GUI | PySide6 (Qt6) |
| Modelos | Pydantic v2 |
| Build | Hatchling |
| Hashing | hashlib + blake3 (opcional) |
| OCR | pytesseract + EasyOCR |
| Imagens | Pillow + NumPy |
| PDF | ReportLab |
| Templates | Jinja2 |

---

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

*Desenvolvido com dedicação para o mercado jurídico brasileiro.*
