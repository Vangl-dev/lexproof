#!/usr/bin/env bash
# Atalhos para rodar e testar o LexProof.
#
#   ./run.sh                 abre o app (janela nova)
#   ./run.sh classico        abre a interface antiga
#   ./run.sh pasta <pasta>   preserva os arquivos da pasta sem abrir a janela e abre o relatório
#       opções: --sem-carimbo                 não usa a internet
#               --periodo 01/03/2026:30/04/2026  limita a conversa ao período
#               --descartar                   com --periodo, apaga o restante da conversa
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
            echo "Uso: ./run.sh pasta <pasta> [--sem-carimbo] [--periodo DD/MM/AAAA:DD/MM/AAAA] [--descartar]"
            exit 1
        fi
        "$PY" - "$2" "${@:3}" <<'PYEOF'
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.ERROR)
from PySide6.QtWidgets import QApplication

from lexproof.ui.simple_window import PreservationWorker
from lexproof.utils.intake import describe_file

from datetime import datetime

folder = Path(sys.argv[1]).resolve()
args = sys.argv[2:]
timestamp = "--sem-carimbo" not in args
discard = "--descartar" in args
period = None
if "--periodo" in args:
    start, _, end = args[args.index("--periodo") + 1].partition(":")
    period = (datetime.strptime(start, "%d/%m/%Y").date(), datetime.strptime(end, "%d/%m/%Y").date())
elif discard:
    sys.exit("--descartar exige --periodo")
files = sorted(f for f in folder.iterdir() if f.is_file() and not f.name.startswith("."))
for f in files:
    info = describe_file(f)
    print(f"  {info.title}: {f.name} ({info.detail})")

app = QApplication([])
worker = PreservationWorker(files, folder.name, "", "Teste pelo run.sh", timestamp,
                            period=period, discard=discard)
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
for em in r.emails:
    status = f"assinatura válida ({em.aligned_signature.domain})" if em.verified else "assinatura NÃO confirmada"
    print(f"E-mail {em.eml_path.name}: de {em.sender}, {len(em.attachments)} anexo(s), {status}")
if r.excerpt is not None:
    e = r.excerpt
    print(f"Recorte: {e.start:%d/%m/%Y} a {e.end:%d/%m/%Y}, {e.kept_messages} de {e.total_messages} mensagens"
          + (f", restante apagado ({len(e.removed_files)} arquivos)" if e.discarded else ", completo guardado lacrado"))
print(f"Conversa: {len(r.messages)} mensagens")
st = r.stitch
if st is not None and st.order:
    print(f"Prints entre si: {len(st.order)} prints, {len(st.messages)} mensagens distintas, "
          f"{len(st.gaps)} lacuna(s), {len(st.contradictions)} contradição(ões), {len(st.issues)} incoerência(s)")
    for g in st.gaps:
        label = "Trecho não printado" if r.screenshot_checks else "Lacuna"
        print(f"    {label} entre {g.before_print} e {g.after_print}: {g.last_before.when} -> {g.first_after.when}")
    for c in st.contradictions:
        print(f"    Contradição {c.when}: {c.print_a} x {c.print_b} {c.differences}")
    for i in st.issues:
        print(f"    {i.print_name}: {i.message}")
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
