# Arquitetura do LexProof

Documento técnico descrevendo a arquitetura, estrutura do projeto, padrões de design e fluxo de dados do LexProof.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Filosofia do Projeto](#filosofia-do-projeto)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Descrição dos Módulos](#descrição-dos-módulos)
- [Fluxo de Dados](#fluxo-de-dados)
- [Padrões de Design](#padrões-de-design)
- [Arquitetura MVVM](#arquitetura-mvvm)
- [Decisões de Arquitetura](#decisões-de-arquitetura)

---

## Visão Geral

O LexProof é uma aplicação desktop construída com Python e PySide6 (Qt6), seguindo uma arquitetura modular com separação clara de responsabilidades. O sistema é projetado para ser extensível, testável e manutenível.

### Princípios Fundamentais

1. **Separação de Responsabilidades**: Cada módulo tem uma responsabilidade única e bem definida
2. **Baixo Acoplamento**: Módulos dependem de abstrações, não de implementações concretas
3. **Alta Coesão**: Código relacionado está agrupado no mesmo módulo
4. **Extensibilidade**: Novos componentes podem ser adicionados sem modificar existentes
5. **Testabilidade**: Componentes podem ser testados independentemente

---

## Filosofia do Projeto

### O que o LexProof NÃO é

- NÃO é um software de criptografia
- NÃO é uma ferramenta para hackers ou informática
- NÃO é um blockchain explorer

### O que o LexProof É

O LexProof é um **software jurídico de preservação técnica de evidências digitais**.

### Objetivo Principal

Permitir que um advogado consiga preservar conversas digitais hoje e demonstrar, meses ou anos depois, exatamente qual era o estado dessas evidências quando foram submetidas ao sistema.

### Papel das Técnicas

A criptografia, OCR, hashes, blockchain e demais técnicas existem para apoiar esse objetivo, não para aparecer em primeiro plano.

---

## Estrutura do Projeto

```
lexproof/
│
├── __init__.py                 # Metadados do pacote (versão, nome)
├── __main__.py                 # Ponto de entrada: cria e executa a aplicação
│
├── core/                       # Framework principal da aplicação
│   ├── __init__.py
│   ├── application.py          # LexProofApplication: bootstrap da QApplication
│   ├── constants.py            # Constantes globais (tipos de arquivo, tamanhos UI)
│   ├── event_bus.py            # EventBus: sistema pub/sub thread-safe
│   └── session.py              # SessionManager: ciclo de vida de casos
│
├── config/                     # Configuração e gerenciamento de caminhos
│   ├── __init__.py
│   ├── paths.py                # Paths: gerenciamento centralizado de diretórios
│   └── settings.py             # Settings (Pydantic): variáveis de ambiente, persistência JSON
│
├── models/                     # Modelos de dados Pydantic v2
│   ├── __init__.py             # Re-exporta todos os modelos
│   ├── evidence.py             # Evidence (base), ImageEvidence, ChatExportEvidence
│   ├── case.py                 # PreservationSession, SessionMetadata
│   ├── hash_result.py          # HashResult, HashAlgorithm
│   ├── metadata.py             # EvidenceMetadata, EXIFData, XMPData
│   ├── ocr_result.py           # OCRResult, OCRConfidence
│   ├── timeline.py             # TimelineEntry, TimelineEntryType
│   ├── correlation.py          # CorrelationResult, CorrelationType
│   ├── quality_grade.py        # QualityGrade, GradeCriteria
│   └── report.py               # ReportConfig, ReportSection
│
├── crypto/                     # Operações criptográficas
│   ├── __init__.py
│   ├── hasher.py               # FileHasher: hashing multi-algoritmo (SHA-256, BLAKE3)
│   └── manifest.py             # ManifestGenerator: criação/validação de manifestos
│
├── perceptual/                 # Hashes perceptuais (v0.4)
│   ├── __init__.py
│   ├── phash.py                # PerceptualHash: pHash, dHash, aHash
│   └── comparator.py           # PerceptualComparator: detecção de similaridade
│
├── ocr/                        # Integração com motores OCR
│   ├── __init__.py
│   ├── base.py                 # BaseOCR: OCR abstrato com pré-processamento
│   ├── processor.py            # OCRProcessor: orquestrador, extração de timestamps/remetentes
│   ├── tesseract_engine.py     # TesseractOCR: integração com Tesseract
│   ├── easyocr_engine.py       # EasyOCREngine: integração com EasyOCR
│   └── preprocessing.py        # Pré-processamento de imagens
│
├── parsers/                    # Parsers de formatos de arquivo
│   ├── __init__.py
│   ├── base.py                 # BaseParser: parser abstrato com detecção de encoding
│   ├── whatsapp_parser.py      # WhatsAppParser: parsing de exportações .txt
│   ├── image_parser.py         # ImageParser: extração EXIF, integração OCR
│   └── archive_parser.py       # ArchiveParser: extração e validação de ZIPs
│
├── correlation/                # Correlacionador print × exportação
│   ├── __init__.py
│   ├── correlator.py           # EvidenceCorrelator: relação print → OCR → TXT → timeline
│   └── matcher.py              # TextMatcher: alinhamento de texto OCR com exportação
│
├── reports/                    # Geração de relatórios
│   ├── __init__.py
│   ├── base.py                 # BaseReportGenerator: preparação comum de dados
│   ├── html_report.py          # HTMLReportGenerator: HTML responsivo com temas
│   ├── pdf_report.py           # PDFReportGenerator: PDF profissional com reportlab
│   ├── qr_generator.py         # QRCodeGenerator: códigos QR de verificação
│   └── methodology.py          # MethodologyGenerator: documentação de procedimentos
│
├── timeline/                   # Análise forense de timeline
│   ├── __init__.py
│   ├── timeline_builder.py     # TimelineBuilder: consolidação multi-fonte
│   └── comparator.py           # TimelineComparator: comparação cross-source
│
├── verification/               # Sistema de verificação
│   ├── __init__.py
│   ├── checker.py              # VerificationChecker: 7 tipos de verificação
│   └── reporter.py             # VerificationReporter: saída formatada
│
├── ui/                         # Interface gráfica PySide6
│   ├── __init__.py
│   ├── main_window.py          # MainWindow: sidebar, tabs, log, status bar, drag-and-drop
│   ├── styles/
│   │   ├── __init__.py
│   │   └── theme.py            # ThemeManager: temas claro/escuro/sistema
│   └── widgets/
│       ├── __init__.py
│       ├── drop_zone.py        # DropZoneWidget: overlay animado de drag-and-drop
│       ├── log_panel.py        # LogPanelWidget: visualizador de log filtrável
│       ├── sidebar.py          # SidebarWidget: seções recolhíveis com animação
│       └── status_bar.py       # StatusBarWidget: barra de progresso e versão
│
└── utils/                      # Funções utilitárias
    ├── __init__.py
    ├── file_utils.py           # Hashing, informações, nomes seguros, detecção MIME
    └── logging_config.py       # Configuração de logging com rotação
```

---

## Descrição dos Módulos

### `core/` - Framework Principal

O módulo `core` é o coração da aplicação, fornecendo os serviços fundamentais:

| Componente | Responsabilidade |
|-----------|-----------------|
| `LexProofApplication` | Bootstrap da aplicação, inicialização do Qt |
| `EventBus` | Sistema de comunicação publish/subscribe thread-safe |
| `SessionManager` | Gerenciamento do ciclo de vida de sessões/casos |
| `constants` | Constantes globais compartilhadas |

**Fluxo de inicialização:**
```
__main__.py → LexProofApplication → EventBus → SessionManager → MainWindow
```

### `config/` - Configuração

Gerencia todas as configurações da aplicação:

- **Settings**: Carrega de variáveis de ambiente (`LEXPROOF_*`), arquivo JSON ou padrões
- **Paths**: Gerencia caminhos de diretórios (logs, output, temp) com criação automática

### `models/` - Modelos de Dados

Modelos Pydantic v2 que definem a estrutura de dados do sistema:

#### Modelo de Evidência (v0.2)

```python
class Evidence(BaseModel):
    """Classe base para todas as evidências."""
    
    id: str  # LP-000001
    file_path: Path
    file_name: str
    file_size: int
    evidence_type: EvidenceType
    source: EvidenceSource  # manual_upload, whatsapp_export, etc.
    
    # Hashes criptográficos
    sha256: str
    blake3: str
    
    # Metadados
    metadata: EvidenceMetadata
    
    # OCR (obrigatório para imagens)
    ocr: Optional[OCRResult]
    
    # Miniatura
    thumbnail: Optional[Path]
    
    # Rastreabilidade
    preservation_date: datetime
    imported_by: Optional[str]
    description: str
    tags: list[str]

class ImageEvidence(Evidence):
    """Evidência do tipo imagem (prints de conversas)."""
    width: int
    height: int
    format: str
    perceptual_hashes: Optional[PerceptualHashes]  # v0.4

class ChatExportEvidence(Evidence):
    """Evidência do tipo exportação de conversa (WhatsApp TXT)."""
    export_format: str  # whatsapp, telegram, etc.
    message_count: int
    date_range: tuple[datetime, datetime]
```

#### Modelo de Sessão (v0.2)

```python
class PreservationSession(BaseModel):
    """Sessão de preservação de evidências."""
    
    id: str  # UUID
    session_code: str  # Código amigável
    
    # Metadados opcionais
    client_name: Optional[str]
    case_number: Optional[str]
    responsible_technician: Optional[str]
    
    # Evidências
    evidence_files: list[Evidence]
    
    # Processamento automático
    timeline: list[TimelineEntry]
    correlations: list[CorrelationResult]
    quality_grade: QualityGrade
    
    # Integridade
    hash_results: list[HashResult]
    
    # Datas
    created_at: datetime
    updated_at: datetime
```

### `crypto/` - Criptografia

Responsável pela integridade criptográfica das evidências:

- **FileHasher**: Suporta SHA-256, BLAKE3; implementa árvore Merkle para hash global
- **ManifestGenerator**: Cria manifestos versionados com hash global para validação posterior

### `perceptual/` - Hashes Perceptuais (v0.4)

Sistema de hashes perceptuais para detecção de similaridade:

- **PerceptualHash**: Implementação de pHash, dHash, aHash
- **PerceptualComparator**: Compara hashes perceptuais e detecta similaridade

**Uso futuro:**
- Detecção de imagens semelhantes
- Detecção de redimensionamentos
- Detecção de recompressão

### `ocr/` - Reconhecimento Óptico de Caracteres

Pipeline completo de OCR:

1. **Pré-processamento**: Escala de cinza, redimensionamento, contraste, remoção de ruído, alinhamento
2. **Extração**: Dois motores (Tesseract, EasyOCR) com fallback automático
3. **Pós-processamento**: Detecção de timestamps, remetentes e segmentação de mensagens

**OCR é obrigatório para imagens** - todo print deve ter texto extraído.

### `parsers/` - Parsers de Arquivo

Cada parser é responsável por um formato específico:

- **WhatsAppParser**: Parsing de exportações `.txt` com detecção de formato de data
- **ImageParser**: Extração EXIF + OCR integrado
- **ArchiveParser**: Extração e validação de ZIPs

### `correlation/` - Correlacionador (v0.2)

Mecanismo que relaciona automaticamente:

```
Print → OCR → Exportação TXT → Timeline
```

**Exemplo de saída:**
```
Print LP-000023
↓
corresponde às linhas 541–548 do arquivo exportado
↓
grau de confiança: 94%
```

### `reports/` - Geração de Relatórios

Sistema flexível de geração de relatórios com estrutura profissional:

#### Estrutura do Relatório (v0.3)
1. Capa
2. Resumo Executivo (linguagem acessível)
3. Dados da Sessão
4. Resumo das Evidências
5. Timeline
6. Evidências preservadas
7. Correspondência OCR × TXT
8. Integridade
9. Metodologia (procedimentos técnicos)
10. Apêndice Técnico
11. Anexos Técnicos

### `timeline/` - Timeline Forense

Análise temporal de evidências:

- **TimelineBuilder**: Consolida dados de múltiplas fontes (TXT + OCR)
- **TimelineComparator**: Compara duas timelines com escore de similaridade

### `verification/` - Sistema de Verificação

Sete verificações automáticas de integridade e consistência:

1. OCR vs TXT
2. Timestamps
3. Remetentes
4. Ordem de mensagens
5. Contagem de mensagens
6. Integridade de arquivos
7. Verificação EXIF

### `ui/` - Interface Gráfica

Interface desktop simplificada com PySide6:

- **MainWindow**: Janela principal com layout modular
- **Fluxo simplificado**: Nova Sessão → Importar Evidências → Gerar Relatório
- **Abas técnicas**: Disponíveis para usuários avançados

---

## Fluxo de Dados

### Fluxo Principal: Preservação de Evidência

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Usuário    │────▶│  UI (Drop    │────▶│  Session      │
│  (Drag &    │     │  Zone)       │     │  Manager      │
│  Drop)      │     └──────────────┘     └───────┬───────┘
└─────────────┘                                  │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Event      │◀────│  Parser      │◀────│  Evidence     │
│  Bus        │     │  (WhatsApp/  │     │  (Model)      │
│             │     │  Image)      │     └───────────────┘
└──────┬──────┘     └──────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Pipeline   │────▶│  Auto        │────▶│  Processado   │
│  Automático │     │  Processing  │     │  Evidence     │
└─────────────┘     └──────────────┘     └───────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Hashes     │────▶│  Metadados   │────▶│  OCR          │
│  SHA-256    │     │  EXIF/XMP    │     │  Texto        │
│  BLAKE3     │     │              │     │  Extraído     │
└─────────────┘     └──────────────┘     └───────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Timeline   │────▶│  Correlação  │────▶│  Verificação  │
│  Cronológica│     │  Print ↔ TXT │     │  Integridade  │
└─────────────┘     └──────────────┘     └───────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Grade      │────▶│  Relatório   │────▶│  Arquivo      │
│  Técnico    │     │  Profissional│     │  Saída        │
└─────────────┘     └──────────────┘     └───────────────┘
```

### Pipeline Automático de Processamento

Todo o processamento é executado automaticamente após importação:

1. **Importação**: Usuário arrasta arquivos para a zona de drop
2. **Parsing**: Sistema identifica tipo de arquivo e extrai dados
3. **Hashes**: Cálculo automático de SHA-256 e BLAKE3
4. **Metadados**: Extração de EXIF, XMP, ICC Profile
5. **OCR**: Extração de texto (obrigatório para imagens)
6. **Timeline**: Reconstrução cronológica automática
7. **Correlação**: Relacionamento print ↔ exportação
8. **Verificação**: Checagem de integridade e consistência
9. **Grade**: Cálculo do índice técnico de qualidade
10. **Relatório**: Geração do documento profissional

**O usuário NÃO executa manualmente cada etapa.**

---

## Padrões de Design

### 1. Publish/Subscribe (Event Bus)

O `EventBus` implementa um sistema de comunicação desacoplado:

```python
# Publicador
event_bus.publish("evidence.imported", {"evidence_id": "LP-000001"})

# Assinante
@event_bus.subscribe("evidence.imported")
def on_evidence_imported(data):
    print(f"Evidência preservada: {data['evidence_id']}")
```

### 2. Strategy Pattern

Usado para algoritmos intercambiáveis:

```python
# OCR Engines
class BaseOCR(ABC):
    @abstractmethod
    def extract_text(self, image: Path) -> OCRResult: ...

class TesseractOCR(BaseOCR): ...
class EasyOCREngine(BaseOCR): ...

# Parsers
class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> Evidence: ...

class WhatsAppParser(BaseParser): ...
class ImageParser(BaseParser): ...
```

### 3. Template Method

Usado em classes abstratas que definem o esqueleto de algoritmos:

```python
class BaseReportGenerator(ABC):
    def generate(self, session: PreservationSession, config: ReportConfig):
        data = self.prepare_data(session)      # Passo comum
        sections = self.build_sections(data)    # Passo abstrato
        content = self.render(sections)         # Passo abstrato
        self.save(content, config.output_path)  # Passo comum
```

### 4. Builder Pattern

Usado para construção de objetos complexos:

```python
session = (PreservationSessionBuilder()
    .with_client("João Silva")
    .with_case_number("12345-67.2024.8.26.0100")
    .with_evidence(evidence1)
    .with_evidence(evidence2)
    .build())
```

---

## Arquitetura MVVM

O LexProof segue uma variação do padrão MVVM adaptado para PySide6:

### Camadas

```
┌─────────────────────────────────────────────────────┐
│                    VIEW (UI)                         │
│  MainWindow, Sidebar, DropZone, LogPanel, StatusBar │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                 VIEWMODEL / SERVICES                 │
│  SessionManager, EventBus, Settings, Paths          │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                     MODEL (Dados)                    │
│  PreservationSession, Evidence, HashResult, etc.    │
└─────────────────────────────────────────────────────┘
```

---

## Decisões de Arquitetura

### 1. Modelo Unificado de Evidência

**Decisão:** Classe base `Evidence` com subclasses para cada tipo

**Justificativa:**
- Representa uniformemente todas as evidências
- Facilita processamento automático
- Permite extensão para novos tipos
- Mantém campos comuns (hashes, metadados, OCR)

### 2. OCR Obrigatório

**Decisão:** OCR é parte obrigatória do pipeline para imagens

**Justificativa:**
- Texto extraído é essencial para correlação
- Permite busca e indexação
- Facilita comparação com exportações
- Agrega valor ao relatório

### 3. Pipeline Automático

**Decisão:** Todo processamento é executado automaticamente

**Justificativa:**
- Elimina erros humanos
- Reduz tempo de processamento
- Garante consistência
- Facilita uso por advogados

### 4. Interface Simplificada

**Decisão:** Fluxo de três passos (Nova Sessão → Importar → Gerar)

**Justificativa:**
- Advogados não são técnicos
- Reduz curva de aprendizado
- Abas técnicas disponíveis para avançados
- Foco no resultado, não no processo

### 5. Relatório como Produto Principal

**Decisão:** Relatório é o principal output do sistema

**Justificativa:**
- Advogados precisam de documento profissional
- Metodologia deve ser reproduzível
- Três níveis de leitura atendem diferentes públicos
- Estrutura segue padrões de laudo técnico

### 6. Ausência de Metadados

**Decisão:** Registrar ausência de metadados como informação, não indício

**Justificativa:**
- Plataformas frequentemente removem metadados
- Ausência não implica fraude
- Transparência é essencial
- Evita interpretações equivocadas

### 7. Índice Técnico (não jurídico)

**Decisão:** Grade A+, A, B, C, D representa qualidade técnica, não valor jurídico

**Justificativa:**
- Evita confusão com avaliação jurídica
- Foca na completude do conjunto preservado
- Transparência sobre limitações
- Orienta o advogado sobre qualidade técnica

---

## Extensibilidade

### Preparação para Future Features

A arquitetura está preparada para:

- **v0.4**: Fingerprints perceptuais (pHash, dHash, aHash)
- **v0.5**: Metadados robustos (EXIF, XMP, ICC Profile)
- **v2.0**: ArchiveBox (preservação de páginas web)
- **v2.0**: OpenTimestamps (timestamping descentralizado)
- **v2.0**: Blockchain (ancoragem de integridade)
- **v2.0**: Assinatura Digital
- **v2.0**: Verificador independente de relatórios
- **v2.0**: Arquivo próprio ".lexproof"

### Pontos de Extensão

```python
# Novo tipo de evidência
class VideoEvidence(Evidence): ...
class AudioEvidence(Evidence): ...
class PDFEvidence(Evidence): ...

# Novo parser
class TelegramParser(BaseParser): ...
class InstagramParser(BaseParser): ...

# Novo motor OCR
class GoogleOCREngine(BaseOCR): ...
class AzureOCREngine(BaseOCR): ...

# Novo âncora blockchain
class EthereumAnchor(BaseAnchor): ...
```

---

## Segurança e Conformidade

### Princípios de Segurança

1. **Integridade**: Hashes garantem que evidências não foram alteradas
2. **Rastreabilidade**: Cadeia de custódia registra todas as operações
3. **Transparência**: Metodologia é documentada e reproduzível
4. **Privacidade**: Dados ficam no ambiente local

### Conformidade

- **LGPD**: Dados processados localmente
- **Marco Legal dos Dados**: Respeito à privacidade
- **Princípios Forenses**: Metodologia reproduzível e transparente

---

## Conclusão

A arquitetura do LexProof é projetada para:

1. **Foco jurídico**: Preservação técnica de evidências
2. **Usabilidade**: Interface simples para advogados
3. **Confiabilidade**: Pipeline automático e verificável
4. **Extensibilidade**: Preparada para futuras funcionalidades
5. **Conformidade**: Respeito a princípios forenses e legais

O sistema é uma ferramenta de preservação, não de análise ou investigação. Seu objetivo é documentar e verificar, não interpretar ou concluir.
