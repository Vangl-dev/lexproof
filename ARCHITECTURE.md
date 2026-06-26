# Arquitetura do LexProof

Documento técnico descrevendo a arquitetura, estrutura do projeto, padrões de design e fluxo de dados do LexProof.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Descrição dos Módulos](#descrição-dos-módulos)
- [Fluxo de Dados](#fluxo-de-dados)
- [Padrões de Design](#padrões-de-design)
- [Arquitetura MVVM](#arquitetura-mvvm)
- [Diagrama de Componentes](#diagrama-de-componentes)
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
│   ├── case.py                 # CaseFile, CaseMetadata
│   ├── custody.py              # CustodyChain, CustodyEvent, CustodyEventType
│   ├── evidence.py             # EvidenceFile, EvidenceType
│   ├── hash_result.py          # HashResult, HashAlgorithm
│   ├── message.py              # WhatsAppMessage, MessageType
│   ├── ocr_result.py           # OCRResult
│   ├── report.py               # ReportConfig, ReportType
│   ├── timeline.py             # TimelineEntry, TimelineEntryType
│   └── verification.py         # VerificationResult, VerificationStatus
│
├── crypto/                     # Operações criptográficas
│   ├── __init__.py
│   ├── hasher.py               # FileHasher: hashing multi-algoritmo, árvore Merkle
│   └── manifest.py             # ManifestGenerator: criação/validação de manifestos
│
├── blockchain/                 # Ancoragem blockchain (opcional)
│   ├── __init__.py
│   ├── base.py                 # BaseAnchor: interface abstrata de ancoragem
│   ├── anchor_manager.py       # AnchorManager: orquestrador multi-backend
│   ├── opentimestamps.py       # OpenTimestampsAnchor: timestamping descentralizado
│   └── rfc3161.py              # RFC3161Anchor: timestamping baseado em TSA
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
│   ├── pdf_parser.py           # PDFParser: extração de texto/metadados de PDFs
│   ├── image_parser.py         # ImageParser: extração EXIF, integração OCR
│   └── archive_parser.py       # ArchiveParser: extração e validação de ZIPs
│
├── reports/                    # Geração de relatórios
│   ├── __init__.py
│   ├── base.py                 # BaseReportGenerator: preparação comum de dados
│   ├── html_report.py          # HTMLReportGenerator: HTML responsivo com temas
│   ├── pdf_report.py           # PDFReportGenerator: PDF profissional com reportlab
│   └── qr_generator.py         # QRCodeGenerator: códigos QR de verificação
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

- **Validação automática** na criação de objetos
- **Serialização** para/from JSON
- **Documentação** integrada via metadados de campo
- **Imutabilidade** por padrão (configurável)

### `crypto/` - Criptografia

Responsável pela integridade criptográfica das evidências:

- **FileHasher**: Suporta SHA-256, SHA3-512, BLAKE3; implementa árvore Merkle para hash global
- **ManifestGenerator**: Cria manifestos versionados com hash global para validação posterior

### `blockchain/` - Ancoragem Blockchain

Sistema opcional de ancoragem de timestamps:

- **BaseAnchor**: Interface abstrata para backends de timestamping
- **OpenTimestampsAnchor**: Timestamping descentralizado ancorado no Bitcoin
- **RFC3161Anchor**: Timestamping baseado em TSA (Certificate Authority)
- **AnchorManager**: Orquestra múltiplos backends com fallback

### `ocr/` - Reconhecimento Óptico de Caracteres

Pipeline completo de OCR:

1. **Pré-processamento**: Escala de cinza, redimensionamento, contraste, remoção de ruído, alinhamento
2. **Extração**: Dois motores (Tesseract, EasyOCR) comFallback automático
3. **Pós-processamento**: Detecção de timestamps, remetentes e segmentação de mensagens

### `parsers/` - Parsers de Arquivo

Cada parser é responsável por um formato específico:

- **WhatsAppParser**: Parsing de exportações `.txt` com detecção de formato de data
- **PDFParser**: Extração de texto e metadados com fallback
- **ImageParser**: Extração EXIF + OCR integrado
- **ArchiveParser**: Extração e validação de ZIPs

### `reports/` - Geração de Relatórios

Sistema flexível de geração de relatórios:

- **HTML**: Layout responsivo com temas, seções colapsáveis, QR codes
- **PDF**: Layout profissional com capa, sumário, tabelas estilizadas
- **QRCode**: Códigos para verificação externa de integridade

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

Interface desktop com PySide6:

- **MainWindow**: Janela principal com layout modular
- **SidebarWidget**: Navegação com seções recolhíveis
- **LogPanelWidget**: Visualização de logs em tempo real
- **DropZoneWidget**: Feedback visual para drag-and-drop
- **ThemeManager**: Sistema de temas com QSS

### `utils/` - Utilitárias

Funções auxiliares compartilhadas:

- **file_utils**: Hashing, informações de arquivo, nomes seguros, detecção MIME
- **logging_config**: Configuração de logging com rotação de arquivos

---

## Fluxo de Dados

### Fluxo Principal: Importação de Evidência

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Usuário    │────▶│  UI (Drop    │────▶│  Session      │
│  (Drag &    │     │  Zone)       │     │  Manager      │
│  Drop)      │     └──────────────┘     └───────┬───────┘
└─────────────┘                                  │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Event      │◀────│  Parser      │◀────│  Evidence     │
│  Bus        │     │  (WhatsApp/  │     │  File         │
│             │     │  PDF/Image)  │     │  (Model)      │
└──────┬──────┘     └──────────────┘     └───────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  File       │────▶│  Manifest    │────▶│  Cadeia de    │
│  Hasher     │     │  Generator   │     │  Custódia     │
└─────────────┘     └──────────────┘     └───────────────┘
       │
       ▼
┌─────────────┐
│  Log Panel  │
│  (UI)       │
└─────────────┘
```

### Fluxo de Verificação

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Evidence   │────▶│  Verification│────▶│  Verification │
│  (Model)    │     │  Checker     │     │  Reporter     │
└─────────────┘     └──────────────┘     └───────┬───────┘
       │                                          │
       ▼                                          ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Hash       │     │  OCR         │     │  Relatório    │
│  Cache      │     │  Processor   │     │  (HTML/PDF)   │
└─────────────┘     └──────────────┘     └───────────────┘
```

### Fluxo de Geração de Relatório

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Case       │────▶│  Report      │────▶│  Arquivo      │
│  Session    │     │  Config      │     │  de Saída     │
└─────────────┘     └──────┬───────┘     │  (HTML/PDF)   │
                           │             └───────────────┘
                           ▼
                    ┌──────────────┐
                    │  QR Code     │
                    │  Generator   │
                    └──────────────┘
```

---

## Padrões de Design

### 1. Publish/Subscribe (Event Bus)

O `EventBus` implementa um sistema de comunicação desacoplado:

```python
# Publicador
event_bus.publish("evidence.imported", {"evidence_id": "123"})

# Assinante
@event_bus.subscribe("evidence.imported")
def on_evidence_imported(data):
    print(f"Evidência importada: {data['evidence_id']}")
```

**Vantagens:**
- Componentes não se conhecem diretamente
- Fácil de adicionar novos listeners
- Suporte a thread-safe via locks

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
    def parse(self, file_path: Path) -> list: ...

class WhatsAppParser(BaseParser): ...
class PDFParser(BaseParser): ...
class ImageParser(BaseParser): ...

# Blockchain Anchors
class BaseAnchor(ABC):
    @abstractmethod
    def anchor(self, data: bytes) -> str: ...

class OpenTimestampsAnchor(BaseAnchor): ...
class RFC3161Anchor(BaseAnchor): ...
```

### 3. Singleton Pattern

Usado para instâncias únicas:

```python
class Settings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Aplicado em:** `Settings`, `ThemeManager`

### 4. Factory Pattern

Usado para criação de objetos baseado em tipo:

```python
class ParserFactory:
    _parsers = {
        "whatsapp": WhatsAppParser,
        "pdf": PDFParser,
        "image": ImageParser,
    }

    @classmethod
    def get_parser(cls, file_type: str) -> BaseParser:
        return cls._parsers[file_type]()
```

### 5. Template Method

Usado em classes abstratas que definem o esqueleto de algoritmos:

```python
class BaseReportGenerator(ABC):
    def generate(self, case: CaseFile, config: ReportConfig):
        data = self.prepare_data(case)      # Passo comum
        template = self.get_template()       # Passo abstrato
        content = self.render(data, template) # Passo abstrato
        self.save(content, config.output_path) # Passo comum
```

### 6. Observer Pattern

Implementado via `EventBus` para notificação de mudanças de estado.

### 7. Builder Pattern

Usado para construção de objetos complexos:

```python
manifest = (ManifestGenerator()
    .add_evidence(evidence)
    .add_timestamp()
    .add_global_hash()
    .build())
```

---

## Arquitetura MVVM

O LexProof segue uma variação do padrão MVVM (Model-View-ViewModel) adaptado para PySide6:

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
│  CaseFile, EvidenceFile, HashResult, WhatsAppMessage│
└─────────────────────────────────────────────────────┘
```

### Separação de Responsabilidades

| Camada | Responsabilidade | Exemplos |
|--------|-----------------|----------|
| **View** | Renderização e interação do usuário | `MainWindow`, `SidebarWidget` |
| **ViewModel** | Lógica de apresentação e orquestração | `SessionManager`, `EventBus` |
| **Model** | Dados e regras de negócio | `CaseFile`, `EvidenceFile` |

### Comunicação entre Camadas

- **View → ViewModel**: Via signals do Qt e EventBus
- **ViewModel → Model**: Via manipulação direta de modelos Pydantic
- **Model → View**: Via eventos publicados no EventBus

### Exemplo de Comunicação

```python
# View publica evento
event_bus.publish("action.import_evidence", {"path": file_path})

# ViewModel (SessionManager) escuta e processa
@event_bus.subscribe("action.import_evidence")
def handle_import(data):
    evidence = parser.parse(data["path"])
    session.add_evidence(evidence)
    event_bus.publish("evidence.imported", {"id": evidence.id})

# View atualiza UI
@event_bus.subscribe("evidence.imported")
def update_ui(data):
    sidebar.update_files()
    log_panel.add_log(f"Evidência {data['id']} importada")
```

---

## Diagrama de Componentes

```
┌──────────────────────────────────────────────────────────────────┐
│                        LexProof Application                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Core      │  │   Config    │  │   Utils     │              │
│  │             │  │             │  │             │              │
│  │ - App       │  │ - Settings  │  │ - File      │              │
│  │ - EventBus  │  │ - Paths     │  │   Utils     │              │
│  │ - Session   │  │             │  │ - Logging   │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                       │
│         ▼                ▼                ▼                       │
│  ┌─────────────────────────────────────────────────────┐        │
│  │                    Models (Pydantic)                  │        │
│  │  CaseFile | EvidenceFile | HashResult | Message | ...│        │
│  └─────────────────────────────────────────────────────┘        │
│         │                │                │                       │
│         ▼                ▼                ▼                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Crypto    │  │   Parsers   │  │   OCR       │              │
│  │             │  │             │  │             │              │
│  │ - Hasher    │  │ - WhatsApp  │  │ - Tesseract │              │
│  │ - Manifest  │  │ - PDF       │  │ - EasyOCR   │              │
│  │             │  │ - Image     │  │ - Processor │              │
│  │             │  │ - Archive   │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│         │                │                │                       │
│         ▼                ▼                ▼                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Blockchain  │  │  Timeline   │  │ Verification│              │
│  │             │  │             │  │             │              │
│  │ - Anchor    │  │ - Builder   │  │ - Checker   │              │
│  │   Manager   │  │ - Comparator│  │ - Reporter  │              │
│  │ - OTS       │  │             │  │             │              │
│  │ - RFC3161   │  │             │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│         │                │                │                       │
│         ▼                ▼                ▼                       │
│  ┌─────────────────────────────────────────────────────┐        │
│  │                    Reports                           │        │
│  │  HTMLReport | PDFReport | QRCodeGenerator            │        │
│  └─────────────────────────────────────────────────────┘        │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────┐        │
│  │                    UI (PySide6)                      │        │
│  │  MainWindow | Sidebar | DropZone | LogPanel | Status │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Decisões de Arquitetura

### 1. PySide6 ao invés de Tkinter/PyQt

**Decisão:** PySide6 (Qt6) como framework de UI

**Justificativa:**
- Licença LGPL (mais permissiva que GPL do PyQt)
- Suporte nativo a threads
- Widgets ricos e maduros
- Estilos QSS para personalização visual
- Suporte a drag-and-drop nativo

### 2. Pydantic para Modelos

**Decisão:** Pydantic v2 para todos os modelos de dados

**Justificativa:**
- Validação automática em tempo de construção
- Serialização JSON nativa
- Type hints completos
- Performance otimizada (Rust core)
- Integração com IDEs

### 3. Lazy Imports

**Decisão:** Imports preguiçosos para bibliotecas pesadas

**Justificativa:**
- Reduz tempo de inicialização
- Permite degradação graciosa quando dependências opcionais estão ausentes
- Economiza memória quando módulos não são usados

**Exemplo:**
```python
def get_ocr_engine(engine_name: str):
    if engine_name == "tesseract":
        from .tesseract_engine import TesseractOCR
        return TesseractOCR()
    elif engine_name == "easyocr":
        from .easyocr_engine import EasyOCREngine
        return EasyOCREngine()
```

### 4. EventBus Centralizado

**Decisão:** Sistema pub/sub thread-safe como canal único de comunicação

**Justificativa:**
- Desacopla componentes
- Facilita adição de novos listeners
- Thread-safe para operações assíncronas
- Fácil de debugar (log centralizado)

### 5. Estrutura Modular

**Decisão:** Módulos independentes com responsabilidade única

**Justificativa:**
- Facilita testes unitários
- Permite desenvolvimento paralelo
- Reduce risco de regressões
- Simplifica refatoração

### 6. Manifestos Versionados

**Decisão:** Manifestos JSON com versionamento e hash global

**Justificativa:**
- Permite validação de integridade retroativa
- Suporta evolução do formato
- Hash global detecta adulterações em qualquer evidência
- Formato legível por humanos e máquinas
