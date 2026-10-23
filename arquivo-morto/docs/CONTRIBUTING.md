# Contribuindo com o LexProof

Obrigado por seu interesse em contribuir com o LexProof! Este guia explicará como configurar seu ambiente de desenvolvimento e enviar suas contribuições.

---

## Sumário

- [Código de Conduta](#código-de-conduta)
- [Como Contribuir](#como-contribuir)
- [Configuração do Ambiente de Desenvolvimento](#configuração-do-ambiente-de-desenvolvimento)
- [Estilo de Código](#estilo-de-código)
- [Requisitos de Testes](#requisitos-de-testes)
- [Processo de Pull Request](#processo-de-pull-request)
- [Relatando Bugs](#relatando-bugs)
- [Sugerindo Funcionalidades](#sugerindo-funcionalidades)

---

## Código de Conduta

Este projeto adota o Código de Conduta do Contributor Covenant. Ao participar, você concorda em cumprir seus termos.

---

## Como Contribuir

### Reportando Bugs

1. Verifique se o bug já foi reportado em [Issues](https://github.com/lexproof/lexproof/issues)
2. Se não existir, abra uma nova issue usando o template de bug
3. Forneça o máximo de detalhes possível (passos para reproduzir, comportamento esperado, comportamento atual)

### Sugerindo Funcionalidades

1. Verifique se a funcionalidade já foi sugerida em [Issues](https://github.com/lexproof/lexproof/issues)
2. Se não existir, abra uma nova issue usando o template de funcionalidade
3. Descreva a funcionalidade, seu caso de uso e benefícios

### Enviando Mudanças

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nome-da-feature`)
3. Faça suas alterações
4. Adicione testes para suas mudanças
5. Certifique-se de que todos os testes passam
6. Faça o commit (`git commit -m 'Adiciona nova funcionalidade'`)
7. Faça o push para sua branch (`git push origin feature/nome-da-feature`)
8. Abra um Pull Request

---

## Configuração do Ambiente de Desenvolvimento

### Pré-requisitos

- Python 3.13 ou superior
- pip
- Git
- Tesseract OCR (para funcionalidade OCR)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/lexproof/lexproof.git
cd lexproof

# Crie um ambiente virtual
python -m venv .venv

# Ative o ambiente virtual
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Instale as dependências de desenvolvimento
pip install -e ".[dev]"

# Instale os hooks de pre-commit
pre-commit install
```

### Configurando o Tesseract OCR

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

#### macOS

```bash
brew install tesseract
```

#### Windows

Baixe o instalador do Tesseract em https://github.com/UB-Mannheim/tesseract/wiki

### Estrutura de Diretórios

Após a instalação, sua estrutura deve estar assim:

```
lexproof/
├── .venv/              # Ambiente virtual
├── lexproof/           # Código-fonte
├── tests/              # Testes
├── pyproject.toml      # Configuração do projeto
└── ...
```

---

## Estilo de Código

### Formatação

Utilizamos as seguintes ferramentas para manter consistência:

- **Ruff**: Linter e formatador
- **Black**: Formatador de código

```bash
# Verificar problemas de lint
ruff check lexproof/

# Formatar código
ruff format lexproof/
# ou
black lexproof/
```

### Regras

1. **Indentação**: Use 4 espaços (não tabs)
2. **Comprimento de linha**: Máximo de 88 caracteres
3. **Imports**: Use `ruff check --fix` para organizar imports automaticamente
4. **Type Hints**: Use type hints em todas as funções públicas
5. **Docstrings**: Use docstrings no formato Google para todas as funções públicas

### Exemplo de Código

```python
def calcular_hash(arquivo: Path, algoritmo: str = "sha256") -> HashResult:
    """Calcula o hash de um arquivo usando o algoritmo especificado.

    Args:
        arquivo: Caminho para o arquivo a ser hasheado.
        algoritmo: Algoritmo de hash a ser usado (padrão: sha256).

    Returns:
        HashResult com o hash calculado e metadados.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o algoritmo não for suportado.
    """
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")

    # Implementação...
    return HashResult(...)
```

### Type Checking

```bash
# Verificar tipos
mypy lexproof/
```

O projeto usa mypy em modo estrito. Certifique-se de que todas as verificações de tipo passem antes de enviar.

---

## Requisitos de Testes

### Estrutura de Testes

```
tests/
├── test_core/
├── test_models/
├── test_crypto/
├── test_parsers/
├── test_ocr/
├── test_timeline/
├── test_verification/
├── test_reports/
├── test_blockchain/
├── test_ui/
└── test_utils/
```

### Escrevendo Testes

1. Coloque os testes no diretório correspondente ao módulo
2. Use o prefixo `test_` para nomes de funções
3. Use classes `Test` para agrupar testes relacionados
4. Use fixtures do pytest para configuração comum

### Exemplo de Teste

```python
import pytest
from pathlib import Path
from lexproof.crypto.hasher import FileHasher

class TestFileHasher:
    """Testes para o FileHasher."""

    def test_calcula_sha256(self, tmp_path):
        """Deve calcular SHA-256 corretamente."""
        arquivo = tmp_path / "teste.txt"
        arquivo.write_text("conteúdo de teste")

        hasher = FileHasher()
        resultado = hasher.calcular_hash(arquivo)

        assert resultado.algoritmo == "sha256"
        assert len(resultado.hash) == 64

    def test_arquivo_nao_existe(self):
        """Deve levantar exceção para arquivo inexistente."""
        hasher = FileHasher()

        with pytest.raises(FileNotFoundError):
            hasher.calcular_hash(Path("/caminho/inexistente.txt"))
```

### Executando Testes

```bash
# Todos os testes
pytest

# Com cobertura
pytest --cov=lexproof

# Relatório HTML de cobertura
pytest --cov=lexproof --cov-report=html

# Testes específicos
pytest tests/test_crypto/test_hasher.py

# Testes com verbose
pytest -v
```

### Cobertura

- Cobertura mínima aceitável: **80%**
- Novos recursos devem incluir testes
- Bug fixes devem incluir testes de regressão

---

## Processo de Pull Request

### Antes de Enviar

1. ✅ Código segue o estilo do projeto (ruff, black, mypy)
2. ✅ Todos os testes existentes passam
3. ✅ Novos testes foram adicionados
4. ✅ Cobertura não diminuiu
5. ✅ Documentação foi atualizada (se aplicável)
6. ✅ Commit messages são claras e descritivas

### Formato do PR

1. **Título**: Descritivo e conciso (ex: "Adiciona suporte a formato X")
2. **Descrição**:
   - O que foi feito
   - Por que foi feito
   - Como testar
   - Screenshots (se aplicável)

### Revisão

1. Um mantenedor revisará seu PR
2. Pode haver pedidos de alteração
3. Após aprovação, seu PR será mergeado

### Commit Messages

Use o formato:

```
<tipo>: <descrição curta>

<descrição opcional mais detalhada>

<footer opcional>
```

Tipos:
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Documentação
- `style`: Formatação (não afeta o código)
- `refactor`: Refatoração
- `test`: Adição/correção de testes
- `chore`: Tarefas de manutenção

---

## Relatando Bugs

Ao reportar um bug, por favor inclua:

1. **Versão do LexProof**: `python -c "import lexproof; print(lexproof.__version__)"`
2. **Sistema operacional**: Linux, macOS, Windows
3. **Versão do Python**: `python --version`
4. **Passos para reproduzir**
5. **Comportamento esperado**
6. **Comportamento atual**
7. **Logs** (se disponíveis em `~/.lexproof/logs/`)
8. **Screenshots** (se aplicável)

---

## Sugerindo Funcionalidades

Ao sugerir uma funcionalidade, por favor inclua:

1. **Problema que resolve**: Qual é o caso de uso?
2. **Solução proposta**: Como você imagina que funcionaria?
3. **Alternativas consideradas**: Você pensou em outras abordagens?
4. **Contexto adicional**: Informações extras que possam ajudar

---

## Perguntas?

Se você tiver dúvidas, abra uma issue com a tag `pergunta` ou entre em contato com a equipe de desenvolvimento.

Obrigado por contribuir com o LexProof! 🚀
