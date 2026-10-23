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

1. **Nova preservação**: nome do caso, responsável e como os arquivos chegaram
   (do próprio celular ou enviados pelo cliente).
2. **Arquivos**: arraste o ZIP de "Exportar conversa" do WhatsApp e os prints
   (ou a pasta com eles). O app já mostra o que é cada arquivo.
3. **Preservar**: o app copia os originais para a pasta do caso, grava o
   SHA-256 de cada um em um manifesto, obtém um carimbo de tempo RFC 3161 e
   confere cada balão dos prints com a conversa exportada.
4. **Resultado**: carimbo, conversa e prints em linguagem simples, com cada
   divergência apontada (texto, data, hora, ordem, contato, mensagem omitida).
5. **Relatório de Preservação e Integridade** em PDF, na pasta do caso.

A interface antiga continua disponível com `lexproof --classico`.

---

## O que o app confere

- **Integridade**: manifesto `preservacao/manifesto-sha256.txt` com o SHA-256
  de cada original.
- **Data**: o manifesto é carimbado por uma TSA (FreeTSA; se falhar, DigiCert
  e depois Sectigo). Só o hash é enviado.
- **Prints × conversa**: o OCR lê cada balão (texto, horário e o separador de
  data acima dele, incluindo "Ontem" e dias da semana, resolvidos pela data do
  print) e procura a mensagem na exportação.

- **Prints entre si** (quando não há exportação, ou além dela): os prints são
  costurados pelas mensagens repetidas entre um e outro; o app aponta lacunas,
  contradições (mesma mensagem com texto diferente), contato ou tamanho de tela
  diferentes e print anterior às mensagens que exibe.
- **E-mail como testemunha**: arraste o `.eml` (Gmail: Mostrar original →
  Baixar original). O app confere a assinatura DKIM do provedor do remetente,
  extrai os anexos e arquiva a chave pública consultada no manifesto carimbado.

O relatório não atesta que o conteúdo é autêntico antes da preservação. Ele
registra o que foi recebido, quando, e o resultado da conferência.

## Como qualquer pessoa confere uma preservação

Na pasta do caso:

```bash
sha256sum -c preservacao/manifesto-sha256.txt
cd preservacao
openssl ts -verify -data manifesto-sha256.txt -in manifesto-sha256.txt.tsr -CAfile freetsa_cacert.pem -untrusted freetsa_tsa.crt
```

O comando exato (que muda conforme a TSA usada) está em
`preservacao/COMO_VERIFICAR.txt`.

Requisitos do sistema: `tesseract` com o idioma `por` (OCR) e `openssl`
(carimbo de tempo).

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
