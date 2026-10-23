# Smart Analysis Engine - Documentação Técnica

## Visão Geral

O Smart Analysis Engine é o módulo de análise inteligente do LexProof. Ele produz um diagnóstico técnico completo do conjunto de evidências de forma **determinística, reproduzível e auditável**.

**Importante:** O motor NÃO utiliza IA generativa ou LLMs. Toda análise é baseada em regras documentadas.

---

## Metodologia

### Princípios Fundamentais

1. **Determinismo**: Mesmas entradas sempre produzem mesmas saídas
2. **Reprodutibilidade**: Qualquer pessoa pode executar a mesma análise
3. **Explicabilidade**: Cada conclusão possui regra, dados e justificativa
4. **Transparência**: Todas as decisões são registradas em logs

### Fluxo de Análise

```
Entrada (Evidências, Mensagens, OCR)
    ↓
Detecção de Plataforma
    ↓
Análise de Composição
    ↓
Análise Cronológica
    ↓
Detecção de Sobreposição
    ↓
Verificação de Ordem
    ↓
Detecção de Continuidade
    ↓
Detecção de Duplicatas
    ↓
Análise de Qualidade
    ↓
Análise de Metadados
    ↓
Análise de Integridade
    ↓
Cálculo de Scores
    ↓
Geração de Recomendações
    ↓
Saída (EvidenceAnalysis)
```

---

## Análises Implementadas

### 1. Detecção de Plataforma

**Objetivo:** Identificar a origem das evidências.

**Algoritmo:**
1. Verificar presença de exportação oficial
2. Analisar formato das mensagens (padrão brasileiro vs internacional)
3. Verificar nomes de arquivos

**Regras:**
- WhatsApp Android: formato `DD/MM/YYYY HH:MM, Nome:`
- WhatsApp iPhone: formato `[DD/MM/YYYY, HH:MM:SS] Nome:`
- Exportação com `_chat.txt`: WhatsApp Android

**Confiança:**
- 90%: Arquivo `_chat.txt` detectado
- 80%: Formato de mensagem consistente
- 70%: Nome contém "whatsapp"
- 30%: Apenas imagens sem exportação

---

### 2. Análise de Composição

**Objetivo:** Contar e classificar evidências.

**Métricas:**
- Quantidade de imagens
- Quantidade de exportações
- Quantidade de participantes
- Período abrangido

---

### 3. Análise Cronológica

**Objetivo:** Detectar lacunas temporais.

**Algoritmo:**
1. Ordenar mensagens por timestamp
2. Calcular intervalo entre mensagens consecutivas
3. Se intervalo > 30 minutos: registrar lacuna

**Limiar:** 30 minutos (configurável)

---

### 4. Detecção de Sobreposição

**Objetivo:** Identificar prints com conteúdo similar.

**Algoritmo:**
1. Extrair texto OCR de cada imagem
2. Calcular similaridade entre pares de imagens
3. Se similaridade > 70%: registrar sobreposição

**Métrica:** Coeficiente de Jaccard sobre tokens

**Fórmula:**
```
similaridade = |A ∩ B| / |A ∪ B|
```

---

### 5. Verificação de Ordem

**Objetivo:** Detectar mensagens fora de ordem cronológica.

**Algoritmo:**
1. Comparar timestamps de mensagens consecutivas
2. Se timestamp anterior > timestamp posterior: problema de ordem

---

### 6. Detecção de Continuidade

**Objetivo:** Identificar mensagens interrompidas.

**Algoritmo:**
1. Verificar se texto termina sem pontuação final
2. Verificar se próxima mensagem é do mesmo remetente
3. Se ambas condições verdadeiras: possível interrupção

**Pontuação final aceita:** `.`, `!`, `?`, `...`

---

### 7. Detecção de Duplicatas

**Objetivo:** Identificar arquivos idênticos.

**Algoritmo:**
1. Comparar hashes SHA-256
2. Se hashes idênticos: arquivo duplicado

**Confiança:** 100% (hash é determinístico)

---

### 8. Análise de Qualidade de Imagens

**Objetivo:** Detectar problemas de qualidade.

**Limiares:**
- Tamanho mínimo: 50 KB (abaixo = comprimida)
- Resolução mínima: 200px (abaixo = ruim para OCR)

---

### 9. Análise de Metadados

**Objetivo:** Verificar presença de EXIF.

**Regra:**
- Se há metadados: registrar dispositivo, data, etc.
- Se não há: informar que plataformas removem metadados
- **NUNCA** tratar ausência de EXIF como fraude

---

### 10. Análise de Integridade

**Objetivo:** Verificar presença de hashes.

**Regra:**
- Se há hash: integridade verificável
- Se não há: integridade não verificável (não necessariamente comprometida)

---

## Índices Técnicos

### Fórmulas

| Score | Fórmula | Descrição |
|-------|---------|-----------|
| OCR Score | `(imagens_com_ocr / total_imagens) × 100` | % de imagens com OCR |
| Timeline Score | `(mensagens_com_timestamp / total_mensagens) × 100` | % de mensagens com timestamp |
| Correlation Score | Baseado em correlações reais | Correlação entre evidências |
| Metadata Score | `(imagens_com_exif / total_imagens) × 100` | % de imagens com metadados |
| Integrity Score | `(evidencias_com_hash / total_evidencias) × 100` | % de evidências com hash |
| Completeness Score | Média ponderada | Score composto |

### Grau Técnico

| Grau | Score Mínimo | Descrição |
|------|--------------|-----------|
| A+ | 90 | Excelente |
| A | 80 | Ótimo |
| B | 70 | Bom |
| C | 60 | Regular |
| D | <60 | Básico |

### Pesos para Cálculo do Grau

| Componente | Peso |
|------------|------|
| Integridade | 25% |
| Completude | 25% |
| Timeline | 20% |
| OCR | 15% |
| Correlação | 10% |
| Metadados | 5% |

---

## Log de Decisões

Cada decisão é registrada com:

```json
{
  "rule": "Regra utilizada",
  "data_analyzed": "Dados analisados",
  "justification": "Justificativa da decisão",
  "confidence": 0.95
}
```

**Exemplos:**
- "Lacuna detectada porque houve intervalo superior a 30 minutos"
- "Print correlacionado utilizando OCR + horário"
- "Mensagem considerada contínua devido ao texto compartilhado"

---

## Limitações

O Smart Analysis Engine possui limitações inerrentes:

1. **Não verifica autenticidade jurídica**
2. **Não verifica autoria das mensagens**
3. **Não verifica veracidade do conteúdo**
4. **Análise de sobreposição é baseada em texto, não visual**
5. **Detecção de plataforma pode não ser precisa para formatos não padronizados**
6. **Ausência de metadados não implica fraude**

---

## Integração com o Pipeline

O Smart Analysis Engine é chamado após a execução do pipeline:

```python
analysis_engine = SmartAnalysisEngine()
analysis = analysis_engine.analyze(
    evidences=result.evidence_files,
    messages=result.messages,
    ocr_results=result.ocr_results,
    correlations=result.correlations,
)
```

### Dados de Entrada
- `evidences`: Lista de evidências catalogadas
- `messages`: Mensagens extraídas do WhatsApp
- `ocr_results`: Resultados de OCR das imagens
- `correlations`: Correlações encontradas

### Dados de Saída
- `findings`: Lista de constatações
- `scores`: Scores técnicos calculados
- `summary`: Resumo da análise
- `health`: Status de saúde do conjunto
- `recommendations`: Recomendações técnicas
- `limitations`: Limitações do sistema
