# Changelog

## [0.43.0] - 2026-07-14

### Melhoria da Experiência do Usuário

#### Pipeline Visual
- Barra de progresso com porcentagem em tempo real
- Descrições humanas para cada etapa do processamento
- Ícones visuais com emojis (○ 🟡 🟢 🔴)
- Tempo de execução exibido por etapa

#### Análise Imediata do ZIP
- Informações exibidas ao detectar o arquivo
- Nome, tamanho, quantidade de arquivos
- Detecção de imagens e exportação WhatsApp

#### Tela de Conclusão
- Resumo com estatísticas do processamento
- Botões para abrir relatório, pasta ou nova preservação
- Mensagens amigáveis sem traceback

#### Descrições Humanas
- "Organizando seus arquivos" (Catalogação)
- "Lendo a conversa do WhatsApp" (Parser)
- "Reconstruindo a ordem das mensagens" (Timeline)
- "Montando relatório" (Relatório)

---

## [0.42.0] - 2026-07-14

### Eliminação de Travamento

#### BLAKE3 Opcional
- Import condicional do módulo blake3
- Continuação do pipeline se BLAKE3 indisponível
- Aviso informativo em vez de erro fatal

#### Tratamento de Falhas
- Timeout de 300 segundos por etapa
- Etapas falhadas marcadas como FAILED
- Pipeline continua mesmo com etapas com falha
- Logs detalhados com tempos por etapa

#### Melhoria dos Logs
- Formato `[N/10] Etapa iniciada...`
- Resumo final com tempos e estatísticas
- Informações úteis em vez de técnicas

---

## [0.41.0] - 2026-07-14

### Integração Completa dos Módulos

#### Conexões Implementadas
- UI → PreservationPipeline (importação inicia pipeline)
- PreservationPipeline → SmartAnalysisEngine (análise técnica)
- SmartAnalysisEngine → PDFReportGenerator (dados no relatório)
- Pipeline → PipelineWidget (progresso visual)
- Dashboard → SessionManager (dados reais)

#### Novos Componentes
- ReportPanelWidget (aba de relatório funcional)
- Conexão automática de sinais Qt

#### Correções
- Extensão de arquivo corrigida (.lexcase → .lexproof.json)
- Duplo connection de sinais removido
- Stub de Preferências implementado

---

## [0.2.0] - 2026-07-01

### Redefinição da Filosofia do Projeto

O LexProof foi redefinido como um **software jurídico de preservação técnica de evidências digitais**, não como um software de criptografia ou ferramenta para hackers.

### Novos Modelos de Dados

#### Modelo de Evidência Unificado
- Criada classe base `Evidence` com identificador único (LP-XXXXXX)
- Adicionados campos obrigatórios: hash SHA-256, hash BLAKE3, metadados, OCR
- Criadas subclasses:
  - `ImageEvidence`: Para prints de conversas
  - `ChatExportEvidence`: Para exportações de WhatsApp e similares

#### Modelo de Sessão de Preservação
- Criada classe `PreservationSession` para representar conjuntos de evidências
- Implementado cálculo automático do índice técnico de qualidade (A+, A, B, C, D)

#### Modelo de Correlação
- Criada classe `CorrelationResult` para correlacionar evidências
- Implementado correlacionador print → OCR → exportação → timeline

### Novos Módulos

#### Módulo de Correlação (`lexproof/correlation/`)
- Implementado `EvidenceCorrelator` para correlação automática
- Suporte a correspondência exata e fuzzy

#### Módulo de Metodologia (`lexproof/reports/`)
- Implementado `MethodologyGenerator` para documentação de procedimentos

### Testes

- Atualizados todos os testes para usar nova estrutura de modelos
- Todos os 232 testes passando

### Correções

- Corrigidos erros de tipo (mypy)
- Corrigidos warnings de lint (ruff)
