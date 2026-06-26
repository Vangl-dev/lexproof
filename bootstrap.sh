#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== LexProof - Bootstrap ==="
echo ""

# Detectar interpretador Python ativo
if command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
elif command -v python &>/dev/null; then
    PYTHON="$(command -v python)"
else
    echo "ERRO: Nenhum interpretador Python encontrado no PATH."
    exit 1
fi

PY_VERSION="$("$PYTHON" --version 2>&1)"
echo "Python detectado: $PYTHON ($PY_VERSION)"

# Criar virtualenv
VENV_DIR="$SCRIPT_DIR/.venv"
if [ -d "$VENV_DIR" ]; then
    echo "Removendo virtualenv anterior..."
    rm -rf "$VENV_DIR"
fi

echo "Criando virtualenv..."
"$PYTHON" -m venv "$VENV_DIR"

# Ativar
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Atualizar pip
echo "Atualizando pip..."
pip install --upgrade pip --quiet

# Instalar dependências
echo "Instalando dependências..."
pip install -e ".[dev]" --quiet

echo ""
echo "=== Ambiente configurado ==="
echo "Python: $(python --version)"
echo "Pytest: $(python -m pytest --version)"
echo ""

# Rodar testes
echo "=== Executando testes ==="
python -m pytest tests/ --tb=short -q

echo ""
echo "=== Concluído ==="
echo "Para ativar o ambiente: source .venv/bin/activate"
