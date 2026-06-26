# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [0.1.0] - 2024-01-01

### Lançamento Inicial - Fases 1 a 10

#### Adicionado

##### Fase 1 - Framework Principal
- Aplicação principal com bootstrap via `QApplication`
- Sistema de constantes globais para tipos de arquivo e tamanhos de UI
- EventBus thread-safe com padrão publish/subscribe tipado
- SessionManager para gerenciamento do ciclo de vida de casos
- Sistema de configuração com `Pydantic Settings` e persistência em JSON
- Gerenciamento centralizado de caminhos de diretórios

##### Fase 2 - Modelos de Dados
- Modelos Pydantic v2 para validação e serialização
- `CaseFile` e `CaseMetadata` para representação de casos
- `EvidenceFile` e `EvidenceType` para evidências digitais
- `HashResult` e `HashAlgorithm` para resultados de hashing
- `CustodyChain`, `CustodyEvent` e `CustodyEventType` para cadeia de custódia
- `WhatsAppMessage` e `MessageType` para mensagens do WhatsApp
- `OCRResult` para resultados de OCR
- `ReportConfig` e `ReportType` para configuração de relatórios
- `TimelineEntry` e `TimelineEntryType` para entradas de timeline
- `VerificationResult` e `VerificationStatus` para resultados de verificação

##### Fase 3 - Criptografia e Integridade
- `FileHasher` com suporte a SHA-256, SHA3-512 e BLAKE3
- Implementação de árvore Merkle para hash global de múltiplos arquivos
- `ManifestGenerator` para geração de manifestos versionados em JSON
- Validação de integridade de manifestos com hash global

##### Fase 4 - Parsers de Arquivo
- `BaseParser` abstrato com detecção de encoding
- `WhatsAppParser` para parsing de exportações `.txt` do WhatsApp
- Detecção automática de formatos de data brasileiro (DD/MM/YYYY) e internacional (MM/DD/YY)
- Classificação de 9 tipos de mensagem
- Extração de remetente e referências de mídia
- `PDFParser` para extração de texto e metadados de PDFs
- `ImageParser` com extração de metadados EXIF e integração OCR
- `ArchiveParser` para extração e validação de arquivos ZIP

##### Fase 5 - OCR
- `BaseOCR` abstrato com pipeline de pré-processamento
- `TesseractOCR` com integração ao Tesseract
- `EasyOCREngine` com integração ao EasyOCR
- `OCRProcessor` como orquestrador multi-motor
- Pipeline de pré-processamento: escala de cinza, redimensionamento, contraste, remoção de ruído, alinhamento
- Detecção de timestamps no texto OCR com múltiplos padrões
- Detecção de remetentes no texto OCR
- Segmentação de mensagens a partir da saída OCR
- Comparação OCR vs TXT para validação cruzada

##### Fase 6 - Timeline Forense
- `TimelineBuilder` para consolidação de múltiplas fontes (TXT + OCR)
- Ordenação cronológica com detecção de duplicatas (tolerância de 1 segundo)
- Detecção de lacunas temporais com limite configurável (padrão: 1 hora)
- Sinalização de inconsistências em entradas afetadas
- `TimelineComparator` para comparação de duas timelines
- Escore de similaridade ponderado (timestamp, remetente, conteúdo)
- Detecção de correspondências, entradas exclusivas e entradas modificadas
- Limiar de correspondência configurável (padrão: 0.85)

##### Fase 7 - Sistema de Verificação
- `VerificationChecker` com 7 tipos de verificação:
  1. Verificação OCR vs TXT
  2. Verificação de timestamps (duplicatas, ordem, anos suspeitos)
  3. Verificação de remetentes (vazios, anomalias, comprimentos)
  4. Verificação de ordem de mensagens
  5. Verificação de contagem de mensagens
  6. Verificação de integridade de arquivos (SHA-256)
  7. Verificação EXIF
- `VerificationReporter` para saída formatada de resultados

##### Fase 8 - Geração de Relatórios
- `HTMLReportGenerator` com layout responsivo e temas claro/escuro
- Seções colapsáveis e suporte a códigos QR
- `PDFReportGenerator` com layout profissional usando ReportLab
- Capa, sumário e tabelas estilizadas
- `QRCodeGenerator` para códigos de verificação
- Configuração de seções (timeline, hashes, OCR, verificação, custódia, QR)

##### Fase 9 - Ancoragem Blockchain
- `BaseAnchor` como interface abstrata de ancoragem
- `OpenTimestampsAnchor` para timestamping descentralizado ancorado no Bitcoin
- `RFC3161Anchor` para timestamping baseado em TSA
- `AnchorManager` como orquestrador multi-backend
- Degradação graciosa quando dependências opcionais estão ausentes

##### Fase 10 - Interface Gráfica Desktop
- `MainWindow` com barra lateral, sistema de abas, painel de log e barra de status
- `SidebarWidget` com seções recolhíveis e animação
- `DropZoneWidget` com overlay animado para drag-and-drop
- `LogPanelWidget` com filtragem (DEBUG/INFO/WARNING/ERROR) e exportação
- `StatusBarWidget` com barra de progresso e rótulo de versão
- `ThemeManager` com temas Claro, Escuro e Sistema
- Sistema de estilos QSS completo
- Barra de menu com atalhos de teclado
- Suporte a drag-and-drop de arquivos

#### Cadeia de Custódia
- Criação automática na importação de evidências
- 6 tipos de evento rastreados
- Rastreamento de hash antes/depois para cada evento

#### Sessão
- Criar, carregar, salvar e fechar sessões
- Arquivos de sessão em formato `.lexproof.json`
- Salvamento automático na importação de evidências
- Reconstrução de cache de hashes ao carregar
