"""Arquivos para análise do conteúdo (skill analise-conversa ou leitura humana).

Grava em ``<caso>/analise/``:

- ``conversa.md``: as mensagens, em ordem, agrupadas por dia, cada uma com
  quem falou, de qual print vem e o resultado da conferência;
- ``prints.json``: o mesmo em formato estruturado, mais a lista de prints com
  a impressão digital de cada um.

O texto vem da conversa exportada quando o print foi conferido com ela; sem
exportação, da leitura dos prints (OCR). Segue o mesmo escopo do relatório:
por padrão, só as mensagens que aparecem nos prints.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from lexproof.reports.text import local_time, person_name, safe_text

SIDE_LABEL = {"left": "esquerda", "right": "direita"}
_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
           "setembro", "outubro", "novembro", "dezembro"]


def long_date(d: date) -> str:
    return f"{_WEEKDAYS[d.weekday()]}, {d.day} de {_MONTHS[d.month - 1]} de {d.year}"


@dataclass
class ExportedMessage:
    date: Optional[date]
    time: Optional[str]
    side: Optional[str]
    sender: str
    text: str
    source: str  # "exportacao" ou "ocr"
    prints: list[str] = field(default_factory=list)
    export_line: Optional[int] = None
    check: str = ""
    # Aviso a inserir depois desta mensagem (lacuna entre prints)
    gap_after: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "data": self.date.isoformat() if self.date else None,
            "hora": self.time,
            "lado": SIDE_LABEL.get(self.side or "", None),
            "remetente": self.sender,
            "texto": self.text,
            "fonte_do_texto": self.source,
            "prints": self.prints,
            "linha_na_exportacao": self.export_line,
            "conferencia": self.check,
            "lacuna_depois": self.gap_after or None,
        }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _contact(checks: list[Any], stitch: Any) -> str:
    # O nome no arquivo da exportação é completo; o do topo do print costuma vir truncado.
    exported = next((c.export_contact for c in checks if getattr(c, "export_contact", None)), None)
    if exported:
        return person_name(exported)
    readings = [c.reading for c in checks] or (list(stitch.order) if stitch is not None else [])
    names = [r.contact for r in readings if r.contact]
    return person_name(max(names, key=len)) if names else ""


def collect_messages(
    messages: list[Any], checks: list[Any], stitch: Any, scope: str
) -> list[ExportedMessage]:
    """Mensagens no escopo do relatório, com lado, remetente e prints de origem."""
    contact = _contact(checks, stitch)
    out: list[ExportedMessage] = []
    if messages and checks:
        by_line: dict[int, ExportedMessage] = {}
        for chk in checks:
            for bc in chk.checks:
                m = bc.message
                if m is None:
                    continue
                em = by_line.get(m.line_number)
                if em is None:
                    em = by_line[m.line_number] = ExportedMessage(
                        date=m.timestamp.date(), time=m.timestamp.strftime("%H:%M"),
                        side=bc.bubble.side, sender=person_name(m.sender),
                        text=safe_text(m.content) or "(sem texto: ligação ou mídia)",
                        source="exportacao", export_line=m.line_number, check=bc.status.label,
                    )
                if chk.reading.path.name not in em.prints:
                    em.prints.append(chk.reading.path.name)
        if scope == "prints":
            out = [by_line[k] for k in sorted(by_line)]
        else:
            for m in messages:
                em = by_line.get(m.line_number) or ExportedMessage(
                    date=m.timestamp.date(), time=m.timestamp.strftime("%H:%M"), side=None,
                    sender=person_name(m.sender),
                    text=safe_text(m.content) or "(sem texto: ligação ou mídia)",
                    source="exportacao", export_line=m.line_number, check="não aparece nos prints",
                )
                out.append(em)
    elif messages and scope != "prints":
        out = [ExportedMessage(
            date=m.timestamp.date(), time=m.timestamp.strftime("%H:%M"), side=None,
            sender=person_name(m.sender), text=safe_text(m.content) or "(sem texto: ligação ou mídia)",
            source="exportacao", export_line=m.line_number, check="sem prints",
        ) for m in messages]
    elif stitch is not None and stitch.messages:
        disputed = {(c.when.split(" ")[-1], safe_text(t)) for c in stitch.contradictions for t in (c.text_a, c.text_b)}
        gap_after = {id(g.last_before): g for g in stitch.gaps}
        for sm in stitch.messages:
            if sm.side == "left":
                sender = contact or "contato"
            elif sm.side == "right":
                sender = "dono do celular que fez os prints"
            else:
                sender = "não identificado"
            text = "(ligação)" if sm.kind == "call" else safe_text(sm.text)
            check = "lido no print; sem exportação para conferir"
            if (sm.time, text) in disputed:
                check = "⚠ CONTRADIÇÃO: outro print mostra esta mensagem com texto diferente (ver relatório)"
            em = ExportedMessage(
                date=sm.date, time=sm.time, side=sm.side, sender=sender, text=text,
                source="ocr", prints=list(sm.sources), check=check,
            )
            g = gap_after.get(id(sm))
            if g is not None:
                em.gap_after = (f"⚠ Lacuna: os prints {g.before_print} e {g.after_print} não têm "
                                f"mensagem em comum; pode haver mensagens não capturadas até "
                                f"{g.first_after.when}. Contexto possivelmente incompleto.")
            out.append(em)
    return out


def write_analysis_files(case_dir: Path, d: dict[str, Any], report_path: Optional[Path]) -> Path:
    """Grava ``analise/conversa.md`` e ``analise/prints.json``; devolve a pasta."""
    out_dir = Path(case_dir) / "analise"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = d.get("metadata", {})
    checks = d.get("screenshot_checks") or []
    stitch = d.get("stitch")
    scope = d.get("transcript_scope") or "prints"
    msgs = [m for m in (d.get("messages") or []) if hasattr(m, "line_number")]
    exported = collect_messages(msgs, checks, stitch, scope)
    contact = _contact(checks, stitch)
    seal = d.get("seal")
    stamped = seal is not None and seal.timestamp is not None

    readings = [c.reading for c in checks] or (list(stitch.order) if stitch is not None else [])
    check_by_name = {c.reading.path.name: c for c in checks}
    prints = []
    for r in readings:
        chk = check_by_name.get(r.path.name)
        prints.append({
            "arquivo": r.path.name,
            "sha256": _sha256(r.path) if r.path.exists() else None,
            "tirado_em": r.captured_at.isoformat() if r.captured_at else None,
            "contato_no_topo": person_name(r.contact),
            "conferencia": (f"{chk.confirmed} de {chk.total} conferem com a exportação" if chk
                            else "sem exportação para conferir"),
        })

    source_note = (
        "conversa exportada do WhatsApp (cada mensagem foi conferida com os prints)"
        if msgs and checks else
        "conversa exportada do WhatsApp" if msgs else
        "leitura dos prints por OCR (não havia conversa exportada); pode ter pequenas imprecisões"
    )
    scope_note = {"prints": "somente as mensagens que aparecem nos prints",
                  "period": "as mensagens do período escolhido",
                  "all": "a conversa inteira"}.get(scope, scope)
    lines = [
        f"# Conversa para análise: {safe_text(meta.get('title', 'caso'))}",
        "",
        f"> Gerado pelo LexProof em {local_time(datetime.now(timezone.utc), with_utc=False)}.",
        "> Os prints originais estão preservados na pasta do caso"
        + (f" e carimbados em {local_time(seal.timestamp.gen_time, with_utc=False)}" if stamped else "")
        + (f"; ver o relatório `{report_path.name}`." if report_path else "."),
        f"> Texto: {source_note}.",
        f"> Escopo: {scope_note}.",
        f"> Lados nos prints: **esquerda** = mensagens recebidas"
        + (f" (contato no topo dos prints: {contact})" if contact else "")
        + "; **direita** = mensagens enviadas pelo dono do celular que fez os prints.",
        "> Este arquivo é uma transcrição auxiliar. A prova são os prints originais preservados.",
        "",
        "## Prints",
        "",
        "| # | Arquivo | Tirado em | SHA-256 | Conferência |",
        "|---|---|---|---|---|",
    ]
    for n, p in enumerate(prints, start=1):
        when = local_time(datetime.fromisoformat(p["tirado_em"]), with_utc=False) if p["tirado_em"] else "não identificado"
        lines.append(f"| {n} | {p['arquivo']} | {when} | `{(p['sha256'] or '-')[:16]}…` | {p['conferencia']} |")
    lines += ["", "## Mensagens"]
    current: Optional[date] = None
    first = True
    for em in exported:
        if em.date != current or first:
            current, first = em.date, False
            lines += ["", f"### {long_date(em.date) if em.date else 'Data não identificada'}", ""]
        side = f" [{SIDE_LABEL[em.side]}]" if em.side in SIDE_LABEL else ""
        origin = ", ".join(em.prints) if em.prints else "—"
        ref = f" · linha {em.export_line} da exportação" if em.export_line else ""
        lines.append(f"- **{em.time or '--:--'} · {em.sender}{side}:** {em.text}")
        lines.append(f"  <small>Fonte: {origin}{ref} · {em.check}</small>")
        if em.gap_after:
            lines += ["", f"> {em.gap_after}", ""]
    (out_dir / "conversa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    data = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "caso": meta.get("title"),
        "relatorio": report_path.name if report_path else None,
        "carimbo": seal.timestamp.gen_time.isoformat() if stamped else None,
        "fonte_do_texto": "exportacao" if msgs else "ocr",
        "escopo": scope,
        "contato": contact,
        "prints": prints,
        "mensagens": [em.as_json() for em in exported],
    }
    (out_dir / "prints.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_dir
