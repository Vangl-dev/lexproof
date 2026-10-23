# Changelog

## [Não lançado]

### Primeiro teste com material real (23/10/2026)
- Falsos alarmes corrigidos: anexos de documento, balões cortados na borda,
  "Ler mais", erros miúdos de leitura do OCR, nome do contato truncado no topo,
  tela de perfil com barra de status, ícones lidos como texto.
- Relatório redesenhado: capa com o resultado geral, resumo em cartões, "Como
  ler este relatório", etiquetas coloridas por mensagem, metodologia aplicada e
  aviso no final, "Página X de Y", fonte Noto Sans.
- Transcrição por padrão só com as mensagens que aparecem nos prints.
- E-mail com a conversa anexada é reconhecido na tela.

### Limpeza
- Interface antiga (`--classico`), "Smart Analysis", relatórios HTML/JSON/ZIP,
  manifesto JSON antigo, OpenTimestamps e documentos desatualizados movidos para
  `arquivo-morto/` (ver o README de lá).

### Clientes que enviam só prints
- E-mail como testemunha: `.eml` com assinatura DKIM conferida no recebimento,
  anexos extraídos (ZIP anexado também é aberto) e chave do provedor arquivada no
  manifesto carimbado.
- Conferência dos prints entre si, sem exportação: costura por sobreposição,
  lacunas, contradições, contato e tamanho de tela, relógio da barra de status.
- Transcrição reconstituída a partir dos prints quando não há exportação.
- Print do perfil do contato: nome e número lidos e conferidos com a conversa.
- Período de interesse: recorte verificável da conversa (linhas copiadas byte a
  byte, conferíveis com `sed | sha256sum`), com opção de apagar o restante e
  guardar só o hash do arquivo completo.

### Preservação verificável
- Carimbo de tempo RFC 3161 real (FreeTSA, com DigiCert e Sectigo como reserva) sobre um
  manifesto SHA-256 dos originais, conferível com `sha256sum` e `openssl` sem o LexProof.
- Conferência dos prints com a conversa exportada: texto, data, hora, ordem, contato,
  momento do print e mensagens omitidas.
- Relatório renomeado para "Relatório de Preservação e Integridade", com aviso de que não
  é laudo pericial, ata notarial nem certificação de autenticidade.

### Correções
- Exportações atuais do WhatsApp não eram reconhecidas (0 mensagens).
- Horários da exportação eram tratados como UTC; agora usam o fuso do celular (Brasília).
- `<Mídia oculta>`, "Mensagem apagada", `<Mensagem editada>` e troca de código de
  segurança passam a ser identificados.

### Interface
- Nova janela em três passos (arquivos → preservação → resultado). A anterior fica em
  `--classico`.


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
