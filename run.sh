#!/usr/bin/env bash
# Atalhos para rodar e testar o LexProof.
#
#   ./run.sh                 abre o app (janela nova)
#   ./run.sh classico        abre a interface antiga
#   ./run.sh pasta <pasta>   preserva os arquivos da pasta sem abrir a janela
#                            e abre o relatório (use --sem-carimbo para não usar a internet)
#   ./run.sh testes          roda os testes automáticos
#   ./run.sh testes-rede     roda os testes, incluindo o carimbo real na FreeTSA
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PY="$SCRIPT_DIR/.venv/bin/python"

if [ ! -x "$PY" ]; then
    echo "Ambiente Python não encontrado; criando com bootstrap.sh..."
    ./bootstrap.sh
fi

check_system() {
    local missing=()
    command -v openssl >/dev/null || missing+=("openssl")
    command -v tesseract >/dev/null || missing+=("tesseract")
    if command -v tesseract >/dev/null && ! tesseract --list-langs 2>/dev/null | grep -qx por; then
        missing+=("tesseract-data-por")
    fi
    if [ ${#missing[@]} -gt 0 ]; then
        echo "Faltam pacotes do sistema: ${missing[*]}"
        echo "Instale com: sudo pacman -S ${missing[*]}"
        exit 1
    fi
}

case "${1:-app}" in
    app)
        check_system
        exec "$PY" -m lexproof
        ;;
    classico)
        check_system
        exec "$PY" -m lexproof --classico
        ;;
    pasta)
        check_system
        if [ -z "${2:-}" ] || [ ! -d "$2" ]; then
            echo "Uso: ./run.sh pasta <pasta com o ZIP e os prints> [--sem-carimbo]"
            exit 1
        fi
        TIMESTAMP=1
        [ "${3:-}" = "--sem-carimbo" ] && TIMESTAMP=0
        "$PY" - "$2" "$TIMESTAMP" <<'PYEOF'
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.ERROR)
from PySide6.QtWidgets import QApplication

from lexproof.ui.simple_window import PreservationWorker
from lexproof.utils.intake import describe_file

folder = Path(sys.argv[1]).resolve()
timestamp = sys.argv[2] == "1"
files = sorted(f for f in folder.iterdir() if f.is_file() and not f.name.startswith("."))
for f in files:
    info = describe_file(f)
    print(f"  {info.title}: {f.name} ({info.detail})")

app = QApplication([])
worker = PreservationWorker(files, folder.name, "", "Teste pelo run.sh", timestamp)
out = {}
worker.step.connect(lambda name, status: status == "running" and print(f"... {name}"))
worker.finished_ok.connect(lambda r, d: out.update(result=r, case_dir=d))
worker.failed.connect(lambda m: out.update(error=m))
worker.run()

if "error" in out:
    sys.exit(f"ERRO: {out['error']}")
r, case_dir = out["result"], out["case_dir"]
print()
if r.seal and r.seal.timestamp:
    print(f"Carimbo: {r.seal.timestamp.gen_time:%d/%m/%Y %H:%M:%S} UTC via {r.seal.timestamp.tsa_url}")
else:
    print(f"Carimbo: não obtido ({(r.seal and r.seal.timestamp_error) or 'desativado'})")
print(f"Conversa: {len(r.messages)} mensagens")
for c in r.screenshot_checks:
    print(f"Print {c.reading.path.name}: {c.confirmed} de {c.total} conferem" + ("" if c.all_ok else "  <-- DIVERGÊNCIAS"))
    for chk in c.divergent:
        print(f"    {chk.status.label}: {chk.bubble.text[:60]!r} {'; '.join(chk.notes)}")
    for m in c.hidden_messages:
        print(f"    Omitida no print: {m.timestamp:%d/%m/%Y %H:%M} {m.content[:60]!r}")
print(f"\nPasta do caso: {case_dir}")
print(f"Relatório: {r.report_path}")
if r.report_path:
    subprocess.Popen(["xdg-open", str(r.report_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
PYEOF
        ;;
    testes)
        exec "$PY" -m pytest -q -p no:cacheprovider "${@:2}"
        ;;
    testes-rede)
        LEXPROOF_NETWORK_TESTS=1 exec "$PY" -m pytest -q -p no:cacheprovider "${@:2}"
        ;;
    *)
        sed -n '2,9p' "$0"
        exit 1
        ;;
esac
