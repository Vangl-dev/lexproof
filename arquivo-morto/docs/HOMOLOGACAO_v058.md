# HOMOLOGACAO_v058.md — Auditoria Tecnica do Laudo Pericial

_Data: 21/07/2026_
_Caso de teste: demo/conversa_whatsapp_export.zip_
_Dados do pipeline: 3 evidencias, 2 imagens, 15 mensagens, 2 correlacoes, 7 verificacoes, 18 timeline entries_

---

## INCONSISTENCIAS ENCONTRADAS

### 1. CRITICA — OCR nunca aparece no laudo (impacto: ALTO)

**Sintoma:** O PDF mostra "OCR nao executado para esta imagem" mesmo quando OCR foi executado.

**Causa raiz:** O campo do modelo e `OCRResult.source_image` (lexproof/models/ocr_result.py:12), mas o PDF usa `getattr(ocr, "file_path", "")` (pdf_report.py:337). O campo `file_path` nao existe em `OCRResult`, entao `_ocr_by()` retorna dict vazio, e `ocr_entry` e sempre `None`.

**Rastreamento:**
- Origem: `OCRProcessor.process_image()` cria `OCRResult(source_image=str(image_path), ...)`
- Campo: `source_image` (nao `file_path`)
- Consumo: `PDFReportGenerator._ocr_by()` usa `getattr(r, "file_path", "")`
- Resultado: Dict vazio, OCR sempre "nao executado"

**Correcao:** Trocar `getattr(r, "file_path", "")` por `getattr(r, "source_image", "")` em `_ocr_by()` e em `_add_apendices()`.

---

### 2. CRITICA — Mensagens nao chegam ao laudo (impacto: ALTO)

**Sintoma:** O Resumo Executivo mostra "Mensagens indexadas: 0" e a Timeline esta vazia, mesmo com 15 mensagens parseadas.

**Causa raiz:** O `report_data` construido em `main_window.py:805` nao inclui a chave `"messages"`. O PDF faz `d.get("messages", d.get("txt_messages", []))` e recebe `[]`.

**Rastreamento:**
- Origem: `WhatsAppParser.parse()` retorna 15 `WhatsAppMessage`
- Pipeline: `result.messages` contem 15 mensagens
- Consumo: `main_window.py` constroi `report_data` SEM chave `"messages"`
- Resultado: PDF recebe lista vazia

**Correcao:** Adicionar `"messages": [vars(m) for m in result.messages]` ao `report_data` em `main_window.py`.

---

### 3. CRITICA — Timeline sempre vazia (impacto: ALTO)

**Sintoma:** A Secao 9 (Linha do Tempo) mostra "Nenhuma mensagem indexada" mesmo com 18 entradas na timeline.

**Causa raiz:** Mesma da #2 — `messages` nao esta no `report_data`, e a timeline e construida a partir das mensagens.

**Correcao:** Depende da correcao #2.

---

### 4. CRITICA — Correlacoes com campos vazios (impacto: ALTO)

**Sintoma:** A Secao 8 mostra "Mensagem correlacionada: | Confianca: | Resultado:" — todos os campos vazios.

**Causa raiz:** `CorrelationResult` nao possui atributos `evidence_name`, `matched_messages`, `confidence`, `result`. O codigo usa `getattr(c, "matched_messages", "")` que retorna `""`. Os dados reais estao em `c.matches[i].confidence`, `c.overall_confidence`, etc.

**Rastreamento:**
- Origem: `EvidenceCorrelator.correlate()` cria `CorrelationResult` com `matches` (lista de `CorrelationMatch`)
- Campo real: `c.matches[0].confidence`, `c.correlation_type.value`
- Consumo: `main_window.py:827` usa `getattr(c, "matched_messages", "")`
- Resultado: Strings vazias

**Correcao:** Mapear corretamente os campos de `CorrelationResult`:
```python
{
    "evidence_name": _resolve_evidence_name(c, evidence_files),
    "matched_messages": str(len(c.matches)),
    "confidence": str(c.overall_confidence),
    "result": c.correlation_type.value,
}
```

---

### 5. ALTA — `overall_confidence` sempre 0.0 (impacto: MEDIO)

**Sintoma:** `c.overall_confidence` e 0.0 apesar de `c.matches[0].confidence` ser 0.8.

**Causa raiz:** `CorrelationResult.add_match()` recalcula a media, mas os matches sao adicionados antes do calculo. O `overall_confidence` inicial e 0.0 e so e atualizado quando `add_match()` e chamado. Se os matches sao criados com a lista default, `overall_confidence` permanece 0.0.

**Correcao:** Recalcular `overall_confidence` apos popular `matches`, ou corrigir no `EvidenceCorrelator`.

---

### 6. MEDIA — Cadeia de custodia so registra importacao (impacto: MEDIO)

**Sintoma:** A cadeia de custodia mostra apenas 3 registros de "Importacao". Faltam: Hash, OCR, EXIF, Parser, Correlacao, Timeline, Relatorio.

**Causa raiz:** `main_window.py` e `preservation.py` constroem `custody_chain` apenas com eventos de importacao.

**Correcao:** Expandir `custody_chain` para incluir todas as etapas do pipeline com horario, duracao e resultado.

---

### 7. MEDIA — Metodologia mostra "0 indexacao(es) de mensagem(ns)" (impacto: MEDIO)

**Sintoma:** A Secao 4 mostra "0 indexacao(es) de mensagem(ns)" apesar de 15 mensagens.

**Causa raiz:** Mesma da #2 — `msg_count = len(msgs) if isinstance(msgs, list) else 0` recebe `[]`.

**Correcao:** Depende da correcao #2.

---

### 8. MINIATURAS — NAO e bug (impacto: NENHUM)

**Sintoma:** A imagem aparece como retangulo verde escuro.

**Diagnostico:** O arquivo `IMG-20240315-WA0001.jpg` e uma imagem 400x600 cujo conteudo e inteiramente a cor RGB(0, 92, 77) — verde escuro/teal. A miniatura e REAL. O retangulo verde e o conteudo real da imagem de teste.

**Conclusao:** Nao e bug. E a imagem de teste que e monocromatica.

---

## RESUMO DE IMPACTO

| # | Inconsistencia | Impacto | Corrigivel? |
|---|----------------|---------|-------------|
| 1 | OCR sempre "nao executado" | ALTO | Sim — 1 linha |
| 2 | Mensagens nao chegam ao PDF | ALTO | Sim — 1 linha |
| 3 | Timeline sempre vazia | ALTO | Sim — depende de #2 |
| 4 | Correlacoes com campos vazios | ALTO | Sim — mapeamento |
| 5 | overall_confidence = 0.0 | MEDIO | Sim — recalculo |
| 6 | Cadeia de custodia incompleta | MEDIO | Sim — expansao |
| 7 | Metodologia: 0 mensagens | MEDIO | Sim — depende de #2 |
| 8 | Miniatura verde | NENHUM | Nao e bug |

---

## QUANTIDADES VERIFICADAS

| Dado | Pipeline | PDF (antes) | PDF (depois) | Status |
|------|----------|-------------|--------------|--------|
| Evidencias | 3 | 3 | 3 | OK |
| Imagens | 2 | 2 | 2 | OK |
| Mensagens | 15 | 0 | 15 | CORRIGIR |
| OCR executados | 2 | 0 ("nao executado") | 2 | CORRIGIR |
| Correlacoes | 2 | 2 (campos vazios) | 2 (campos preenchidos) | CORRIGIR |
| Hashes | 6 | 6 | 6 | OK |
| Verificacoes | 7 | 7 | 7 | OK |
| Timeline entries | 18 | 0 | 18 | CORRIGIR |
| Grau tecnico | A+ | A+ | A+ | OK |
| Duracao | 1.39s | N/D | 1.39s | CORRIGIR |
| Cadeia de custodia | 3 (import only) | 3 | Completa | CORRIGIR |

---

## CORRECOES NECESSARIAS (priorizadas)

1. **pdf_report.py:337** — `getattr(r, "file_path", "")` → `getattr(r, "source_image", "")`
2. **pdf_report.py:1075** — `getattr(ocr, "file_path", "")` → `getattr(ocr, "source_image", "")`
3. **main_window.py:805** — Adicionar `"messages"` ao `report_data`
4. **main_window.py:827** — Mapear campos de `CorrelationResult` corretamente
5. **pdf_report.py** — Recalcular `overall_confidence` ou corrigir no pipeline
6. **main_window.py** — Expandir `custody_chain` para incluir todas as etapas
