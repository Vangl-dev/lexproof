# Problemas Conhecidos - LexProof

Lista de problemas **reais** encontrados durante testes. Apenas problemas reproduzidos.

---

## v0.42 - Corrigidos

### Pipeline travava com BLAKE3 indisponível
- **Status:** Corrigido ✓
- **Problema:** Pipeline travava indefinidamente quando blake3 não estava instalado
- **Causa:** Import direto de `blake3` no topo de `hasher.py`
- **Correção:** Import condicional com try/except
- **Impacto:** Crítico - impedia qualquer processamento

### Etapas do pipeline ficavam penduradas
- **Status:** Corrigido ✓
- **Problema:** Etapa "Aguardando" permanecia indefinidamente
- **Causa:** Sem timeout para etapas
- **Correção:** Timeout de 300 segundos por etapa
- **Impacto:** Alto - usuário achava que o programa travou

### Erros interrompiam o pipeline
- **Status:** Corrigido ✓
- **Problema:** Falha em uma etapa parava todo o processamento
- **Causa:** Exceções não tratadas adequadamente
- **Correção:** Try/except em cada etapa com continuação
- **Impacto:** Alto - processamento nunca completava

---

## v0.43 - Corrigidos

### Interface sem feedback durante processamento
- **Status:** Corrigido ✓
- **Problema:** Usuário não sabia se o processamento estava funcionando
- **Causa:** Sem barra de progresso ou indicação visual
- **Correção:** Barra de progresso com porcentagem
- **Impacto:** Médio - gera ansiedade no usuário

### Sem descrições das etapas
- **Status:** Corrigido ✓
- **Problema:** Nomes técnicos como "Parser" não eram compreensíveis
- **Causa:** Nomes de etapas muito técnicos
- **Correção:** Descrições humanas ("Lendo a conversa do WhatsApp")
- **Impacto:** Médio - dificulta acompanhamento

### Sem tela de conclusão
- **Status:** Corrigido ✓
- **Problema:** Usuário não sabia quando o processamento terminava
- **Causa:** Sem resumo ou indicação de conclusão
- **Correção:** Tela de resumo com estatísticas e botões
- **Impacto:** Médio - usuário não sabia o que fazer depois

---

## Pendentes

### OCR depende do Tesseract
- **Status:** Aberto
- **Problema:** OCR não funciona sem Tesseract instalado no sistema
- **Causa:** Dependência externa do sistema operacional
- **Impacto:** Médio - funcionalidade limitada sem Tesseract
- **Solução:** Documentar instalação claramente ou usar fallback

### BLAKE3 é opcional
- **Status:** Aberto (comportamento esperado)
- **Problema:** Hash BLAKE3 não é calculado se blake3 não está instalado
- **Causa:** Dependência opcional
- **Impacto:** Baixo - SHA-256 é suficiente para maioria dos casos
- **Solução:** Já tratado com aviso e continuação

### QFileDialog padrão pouco amigável
- **Status:** Aberto
- **Problema:** Seletor de arquivos do sistema é genérico e pouco intuitivo
- **Causa:** Usa QFileDialog nativo do Qt
- **Impacto:** Baixo - funciona mas não é ideal
- **Solução:** Personalizar ou usar seletor customizado (futuro)

### Contraste visual em alguns temas
- **Status:** Aberto
- **Problema:** Alguns elementos podem ter baixo contraste em temas escuros
- **Causa:** Paleta de cores não testada em todos os contextos
- **Impacto:** Baixo - questão de acessibilidade
- **Solução:** Revisar paleta de cores por tema

### Necessidade de validar com diversos ZIPs
- **Status:** Aberto
- **Problema:** Apenas 1 ZIP real testado até agora
- **Causa:** Início dos testes de usuário
- **Impacto:** Alto - pode haver bugs em formatos diferentes
- **Solução:** Testar com 10+ ZIPs de diferentes plataformas

---

## Não Reproduzidos (Hipóteses Removidas)

Nenhum. Apenas problemas reproduzidos são listados neste documento.
