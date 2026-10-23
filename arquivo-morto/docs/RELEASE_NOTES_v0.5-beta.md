# Release Notes - v0.5-beta

Primeiro release beta interno do LexProof.

---

## Sobre Esta Versão

Esta versão marca o início da fase de **Estabilização** do LexProof. O produto já possui fluxo funcional completo, desde a importação de um ZIP do WhatsApp até a geração automática de um relatório PDF.

---

## O Que Já Funciona

### Fluxo Principal
- ✓ Importação de ZIPs exportados do WhatsApp
- ✓ Detecção automática de tipo de evidência
- ✓ Pipeline completo de processamento
- ✓ Análise técnica determinística (Smart Analysis)
- ✓ Geração de relatório PDF profissional
- ✓ Abertura automática do relatório

### Interface
- ✓ Dashboard com ações principais
- ✓ Pipeline visual com barra de progresso
- ✓ Descrições humanas para cada etapa
- ✓ Tela de conclusão com resumo
- ✓ Abas: Evidências, Hashes, Timeline, Pipeline, Relatório
- ✓ Drag-and-drop para importação
- ✓ Log de eventos
- ✓ Temas claro/escuro

### Processamento
- ✓ Catalogação de evidências
- ✓ Extração de metadados
- ✓ Cálculo de hashes (SHA-256)
- ✓ OCR de imagens (com Tesseract)
- ✓ Parser de conversas WhatsApp
- ✓ Correlação prints × conversa
- ✓ Reconstrução cronológica
- ✓ Verificação de integridade
- ✓ Classificação técnica de qualidade

### Tratamento de Erros
- ✓ BLAKE3 opcional (continua sem ele)
- ✓ Timeout por etapa (300 segundos)
- ✓ Erros tratados sem travamento
- ✓ Logs detalhados para diagnóstico

---

## O Que Ainda Não Funciona

### Limitações Conhecidas
- ✗ OCR depende do Tesseract instalado no sistema
- ✗ BLAKE3 opcional (hash adicional não calculado sem ele)
- ✗ Suporte limitado a WhatsApp (outras plataformas não testadas)
- ✗ QFileDialog padrão pouco amigável
- ✗ Contraste visual pode ter problemas em alguns temas

### Funcionalidades Não Implementadas
- ✗ Suporte a Telegram, Messenger, Instagram, Facebook
- ✗ Internacionalização
- ✗ Plugin system
- ✗ Exportação para sistemas jurídicos (e-SAJ, PJe)
- ✗ Assinatura digital
- ✗ Ancoragem blockchain

---

## Dependências

### Obrigatórias
```
Python >= 3.10
PySide6 >= 6.6.0
pydantic >= 2.5.0
reportlab >= 4.0.0
Pillow >= 10.0.0
pytesseract >= 0.3.10
```

### Opcionais
```
blake3 >= 1.0.0  # Hash adicional
easyocr >= 1.7.0  # Motor OCR alternativo
```

### Do Sistema
```
Tesseract OCR  # Para funcionalidade completa de OCR
```

---

## Casos Recomendados

### Ideal Para
- ZIPs exportados do WhatsApp Android
- Conversas com texto e prints
- ZIPs com tamanho razoável (< 100MB)

### Ainda Não Suportado
- ZIPs de outras plataformas (Telegram, etc.)
- ZIPs com vídeos ou áudios
- ZIPs muito grandes (> 1GB)
- ZIPs corrompidos

---

## Como Usar

### Instalação

```bash
git clone https://github.com/lexproof/lexproof.git
cd lexproof
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Execução

```bash
python -m lexproof
```

### Fluxo

1. Clique em "Importar Evidências" ou arraste um ZIP
2. Selecione o arquivo ZIP do WhatsApp
3. Acompanhe o processamento na aba Pipeline
4. O relatório PDF será aberto automaticamente

---

## Known Issues

Veja [KNOWN_ISSUES.md](KNOWN_ISSUES.md) para lista completa de problemas conhecidos.

---

## Próximos Passos

1. Testar com 10+ ZIPs reais
2. Corrigir bugs encontrados
3. Melhorar UX baseada em feedback
4. Validar relatório PDF
5. Documentar limitações

---

## Feedback

Para reportar problemas ou sugestões, abra uma issue no GitHub.

---

*Release preparado para testes internos.*
