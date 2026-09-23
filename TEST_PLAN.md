# Plano de Validação - LexProof

Plano oficial de testes para validação do produto.

---

## Visão Geral

**Objetivo:** Validar que o LexProof processa corretamente diferentes tipos de evidências.

**Critério de sucesso:** 10+ ZIPs processados com sucesso, sem travamentos, com relatório válido.

---

## Cenários de Teste

### WhatsApp Android

#### Teste WA-01: ZIP básico
- **Objetivo:** Processar ZIP simples do WhatsApp Android
- **Dados:** ZIP com 10-20 mensagens de texto
- **Resultado esperado:** Pipeline completo, relatório gerado
- **Status:** Pendente

#### Teste WA-02: ZIP com imagens
- **Objetivo:** Processar ZIP com prints de conversa
- **Dados:** ZIP com mensagens e 5-10 imagens
- **Resultado esperado:** OCR executado, correlações encontradas
- **Status:** Pendente

#### Teste WA-03: ZIP grande
- **Objetivo:** Processar ZIP com muitos arquivos
- **Dados:** ZIP com 100+ arquivos
- **Resultado esperado:** Processamento completo sem timeout
- **Status:** Pendente

#### Teste WA-04: ZIP com mídia ocultada
- **Objetivo:** Processar ZIP com mensagens de mídia ocultada
- **Dados:** ZIP com `<Mídia ocultada>`
- **Resultado esperado:** Mensagens processadas normalmente
- **Status:** Pendente

---

### WhatsApp iPhone

#### Teste WI-01: ZIP básico
- **Objetivo:** Processar ZIP do WhatsApp iPhone
- **Dados:** ZIP com formato `[DD/MM/YYYY, HH:MM:SS] Nome:`
- **Resultado esperado:** Parser detecta formato iPhone
- **Status:** Pendente

---

### Telegram

#### Teste TG-01: Exportação HTML
- **Objetivo:** Processar exportação do Telegram
- **Dados:** Arquivo HTML exportado
- **Resultado esperado:** Mensagens extraídas (se suportado)
- **Status:** Pendente (suporte limitado)

---

### Messenger

#### Teste MS-01: Exportação HTML
- **Objetivo:** Processar exportação do Messenger
- **Dados:** Arquivo HTML exportado
- **Resultado esperado:** Mensagens extraídas (se suportado)
- **Status:** Pendente (suporte limitado)

---

### Instagram

#### Teste IG-01: Mensagens diretas
- **Objetivo:** Processar exportação do Instagram
- **Dados:** Arquivo de mensagens
- **Resultado esperado:** Mensagens extraídas (se suportado)
- **Status:** Pendente (suporte limitado)

---

### Facebook

#### Teste FB-01: Mensagens
- **Objetivo:** Processar exportação do Facebook
- **Dados:** Arquivo de mensagens
- **Resultado esperado:** Mensagens extraídas (se suportado)
- **Status:** Pendente (suporte limitado)

---

### Cenários Especiais

#### Teste SE-01: ZIP válido sem TXT
- **Objetivo:** Processar ZIP com apenas imagens
- **Dados:** ZIP com 10 imagens, sem arquivo .txt
- **Resultado esperado:** OCR executado, sem parser WhatsApp
- **Status:** Pendente

#### Teste SE-02: ZIP sem imagens
- **Objetivo:** Processar ZIP com apenas TXT
- **Dados:** ZIP com arquivo .txt, sem imagens
- **Resultado esperado:** Parser executado, sem OCR
- **Status:** Pendente

#### Teste SE-03: Muitas imagens
- **Objetivo:** Processar ZIP com muitas imagens
- **Dados:** ZIP com 50+ imagens
- **Resultado esperado:** OCR completo, sem timeout
- **Status:** Pendente

#### Teste SE-04: Imagem gigante
- **Objetivo:** Processar imagem de grande porte
- **Dados:** ZIP com imagem > 10MB
- **Resultado esperado:** Processamento completo
- **Status:** Pendente

#### Teste SE-05: Arquivos duplicados
- **Objetivo:** Detectar arquivos duplicados
- **Dados:** ZIP com imagens idênticas
- **Resultado esperado:** Duplicatas detectadas na análise
- **Status:** Pendente

#### Teste SE-06: ZIP corrompido
- **Objetivo:** Tratar ZIP inválido
- **Dados:** ZIP corrompido ou inválido
- **Resultado esperado:** Erro tratado graciosamente
- **Status:** Pendente

#### Teste SE-07: ZIP vazio
- **Objetivo:** Tratar ZIP sem conteúdo
- **Dados:** ZIP vazio ou com apenas pastas
- **Resultado esperado:** Erro tratado graciosamente
- **Status:** Pendente

#### Teste SE-08: Múltiplos TXTs
- **Objetivo:** Processar ZIP com vários TXTs
- **Dados:** ZIP com 3+ arquivos .txt
- **Resultado esperado:** Todos processados
- **Status:** Pendente

---

## Execução

### Comando para executar testes

```bash
# Teste manual via interface
python -m lexproof

# Teste automatizado (futuro)
pytest tests/integration/test_real_cases.py
```

### Registro de Resultados

Para cada teste, registrar:
- Data de execução
- Ambiente
- Arquivo utilizado
- Resultado obtido
- Problemas encontrados
- Screenshots (se aplicável)

---

## Métricas

### Critérios de Aprovação

| Métrica | Meta |
|---------|------|
| ZIPs processados | 10+ |
| Taxa de sucesso | 90%+ |
| Sem travamentos | 100% |
| Relatório válido | 100% |
| Erros tratados | 100% |

### Status Geral

| Cenário | Total | Concluídos | Aprovados |
|---------|-------|------------|-----------|
| WhatsApp Android | 4 | 0 | 0 |
| WhatsApp iPhone | 1 | 0 | 0 |
| Telegram | 1 | 0 | 0 |
| Messenger | 1 | 0 | 0 |
| Instagram | 1 | 0 | 0 |
| Facebook | 1 | 0 | 0 |
| Especiais | 8 | 0 | 0 |
| **Total** | **17** | **0** | **0** |
