# Roadmap de Desenvolvimento

Plano de desenvolvimento do LexProof com status das fases e funcionalidades futuras.

---

## Fases Concluídas

### Fase 1 - Framework Principal ✅
- Aplicação principal com bootstrap
- Sistema de constantes globais
- EventBus thread-safe
- SessionManager
- Sistema de configuração
- Gerenciamento centralizado de caminhos

### Fase 2 - Modelos de Dados ✅
- Modelos Pydantic v2 completos
- CaseFile, EvidenceFile, HashResult
- CustodyChain, WhatsAppMessage
- OCRResult, ReportConfig
- TimelineEntry, VerificationResult

### Fase 3 - Criptografia e Integridade ✅
- FileHasher multi-algoritmo
- Árvore Merkle
- ManifestGenerator
- Validação de integridade

### Fase 4 - Parsers de Arquivo ✅
- WhatsAppParser
- PDFParser
- ImageParser
- ArchiveParser
- BaseParser abstrato

### Fase 5 - OCR ✅
- TesseractOCR
- EasyOCREngine
- OCRProcessor
- Pipeline de pré-processamento
- Detecção de timestamps e remetentes
- Comparação OCR vs TXT

### Fase 6 - Timeline Forense ✅
- TimelineBuilder
- TimelineComparator
- Detecção de duplicatas e lacunas
- Consolidação multi-fonte

### Fase 7 - Sistema de Verificação ✅
- 7 tipos de verificação
- VerificationChecker
- VerificationReporter

### Fase 8 - Geração de Relatórios ✅
- HTMLReportGenerator
- PDFReportGenerator
- QRCodeGenerator
- Temas claro/escuro

### Fase 9 - Ancoragem Blockchain ✅
- OpenTimestampsAnchor
- RFC3161Anchor
- AnchorManager
- Degradação graciosa

### Fase 10 - Interface Gráfica Desktop ✅
- MainWindow completa
- SidebarWidget recolhível
- DropZoneWidget animado
- LogPanelWidget filtrável
- StatusBarWidget com progresso
- ThemeManager multi-tema
- Atalhos de teclado

---

## Fases em Andamento

### Fase 11 - Testes Unitários 🔄
- Testes para módulo `core/`
- Testes para módulo `models/`
- Testes para módulo `crypto/`
- Testes para módulo `parsers/`
- Testes para módulo `ocr/`
- Testes para módulo `timeline/`
- Testes para módulo `verification/`
- Testes para módulo `reports/`
- Testes para módulo `blockchain/`
- Testes para módulo `ui/`
- Testes para módulo `utils/`
- Cobertura mínima de 80%

### Fase 12 - Testes de Integração 🔄
- Testes de fluxo completo (importação → verificação → relatório)
- Testes de UI com pytest-qt
- Testes de performance

---

## Fases Planejadas

### Fase 13 - Internacionalização 📋
- Sistema i18n com suporte a múltiplos idiomas
- Tradução para inglês (en_US)
- Tradução para espanhol (es_ES)
- Interface traduzível via arquivos `.ts`

### Fase 14 - Plugin System 📋
- Arquitetura de plugins para extensibilidade
- Interface de plugin padrão
- Carregamento dinâmico de plugins
- Marketplace de plugins

### Fase 15 - Exportação Avançada 📋
- Exportação para formato e-SAJ
- Exportação para formato PJe
- Integração com sistemas de gestão jurídica
- Exportação em lote

### Fase 16 - Análise Estatística 📋
- Dashboard com métricas de casos
- Gráficos de atividade temporal
- Estatísticas de comunicação
- Relatórios comparativos entre casos

### Fase 17 - Backup e Sincronização 📋
- Backup automático de casos
- Sincronização entre dispositivos
- Criptografia de backup
- Restauração de versões anteriores

### Fase 18 - API REST 📋
- API para acesso programático
- Autenticação via tokens
- Documentação OpenAPI/Swagger
- Integração com sistemas externos

### Fase 19 - Modo Colaborativo 📋
- Compartilhamento seguro de casos
- Controle de acesso baseado em papéis
- Histórico de contribuições por usuário
- Comentários e anotações colaborativas

### Fase 20 - Certificação e Conformidade 📋
- Certificação ICP-Brasil
- Conformidade com Marco Legal dos Dados
- Adequação à LGPD
- Validação perante tribunais

---

## Funcionalidades Futuras (Backlog)

- [ ] Suporte a formatos de mídia adicionais (MP4, AVI, MOV)
- [ ] Reconhecimento facial em imagens
- [ ] Análise de metadados de redes sociais
- [ ] Detecção de manipulação de imagens
- [ ] Suporte a nuvem (AWS, Azure, GCP)
- [ ] Modo offline completo
- [ ] Atualização automática
- [ ] Telemetria opcional
- [ ] Temas personalizáveis
- [ ] Atalhos de teclado customizáveis
- [ ] Modo acessibilidade aprimorado
- [ ] Suporte a múltiplos monitores
- [ ] Modo compacto para telas pequenas
- [ ] Integração com assistentes de voz
- [ ] Exportação para formatos jurídicos internacionais
