"""Janela principal simplificada do LexProof.

Tres telas em sequencia: escolher os arquivos, acompanhar a preservacao e
ver o resultado. Tudo o que importa para o usuario aparece em linguagem
simples; os detalhes tecnicos ficam no relatorio.
"""

from __future__ import annotations

import html
import json
import logging
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QDate, QSettings, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QDragEnterEvent, QDropEvent, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lexproof.config.paths import Paths
from lexproof.core.session import SessionManager
from lexproof.utils.intake import (
    KIND_EMAIL,
    KIND_EXPORT,
    KIND_SCREENSHOT,
    FileInfo,
    describe_file,
    intake_warnings,
)

logger = logging.getLogger(__name__)

PRIMARY = "#1a237e"
SUCCESS = "#2e7d32"
WARNING = "#b26a00"
DANGER = "#c62828"
MUTED = "#5f6368"
BORDER = "#dadce0"
SURFACE = "#f6f7fb"

RECEIVED_OPTIONS = [
    "Do meu próprio celular",
    "Enviados pelo cliente por e-mail ou nuvem",
    "Enviados pelo cliente pelo WhatsApp (como documento)",
    "Outro",
]

# Passos exibidos ao usuario, na ordem, e as etapas do pipeline que os compoem.
VISIBLE_STEPS = [
    ("copy", "Copiar os arquivos originais para a pasta do caso"),
    ("Hashes", "Calcular a impressão digital (SHA-256) de cada arquivo"),
    ("Recorte do período", "Recortar a conversa ao período de interesse"),
    ("Carimbo de tempo", "Obter o carimbo de tempo"),
    ("Parser", "Ler a conversa exportada"),
    ("Conferência dos prints", "Conferir cada print com a conversa"),
    ("Relatório", "Gerar o relatório em PDF"),
]

STYLESHEET = f"""
QWidget {{ font-size: 10.5pt; color: #202124; }}
QMainWindow, QWidget#page {{ background: white; }}
QLabel#appTitle {{ font-size: 15pt; font-weight: 600; color: {PRIMARY}; }}
QLabel#appSubtitle {{ color: {MUTED}; }}
QLabel#pageTitle {{ font-size: 18pt; font-weight: 600; }}
QLabel#cardTitle {{ font-size: 12pt; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#warning {{ color: {WARNING}; }}
QFrame#header {{ background: white; border-bottom: 1px solid {BORDER}; }}
QFrame#card {{ background: white; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#dropZone {{ background: {SURFACE}; border: 2px dashed #9aa0d4; border-radius: 10px; }}
QFrame#dropZone[active="true"] {{ background: #e8eaf6; border-color: {PRIMARY}; }}
QFrame#banner {{ border-radius: 10px; }}
QLineEdit, QComboBox {{ padding: 7px 9px; border: 1px solid {BORDER}; border-radius: 6px; background: white; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {PRIMARY}; }}
QPushButton {{ padding: 8px 16px; border: 1px solid {BORDER}; border-radius: 6px; background: white; }}
QPushButton:hover {{ background: {SURFACE}; }}
QPushButton#primary {{ background: {PRIMARY}; color: white; border: none; font-weight: 600; padding: 10px 22px; }}
QPushButton#primary:hover {{ background: #283593; }}
QPushButton#primary:disabled {{ background: #c5cae9; }}
QPushButton#link {{ border: none; color: {PRIMARY}; padding: 2px; text-decoration: underline; background: transparent; }}
QPushButton#remove {{ border: none; color: {MUTED}; padding: 2px 8px; background: transparent; }}
QListWidget, QTreeWidget {{ border: 1px solid {BORDER}; border-radius: 8px; }}
QProgressBar {{ border: none; background: #e8eaf6; border-radius: 4px; height: 8px; }}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 4px; }}
"""


def _label(text: str, name: str = "", wrap: bool = True) -> QLabel:
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lbl


def _card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 16, 20, 18)
    layout.setSpacing(10)
    return frame, layout


def _open_path(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


# ---------------------------------------------------------------------- #
# Processamento em segundo plano
# ---------------------------------------------------------------------- #


class PreservationWorker(QThread):
    """Copia os arquivos para o caso e executa o pipeline."""

    step = Signal(str, str)  # (etapa, status)
    finished_ok = Signal(object, object)  # (PipelineResult, pasta do caso)
    failed = Signal(str)

    def __init__(
        self,
        files: list[Path],
        case_name: str,
        responsible: str,
        received_via: str,
        timestamp: bool,
        *,
        period: Optional[tuple[Any, Any]] = None,
        discard: bool = False,
    ) -> None:
        super().__init__()
        self._files = files
        self._case_name = case_name
        self._responsible = responsible
        self._received_via = received_via
        self._timestamp = timestamp
        self._period = period
        self._discard = discard

    def run(self) -> None:
        try:
            from lexproof.pipeline.preservation import PreservationPipeline

            self.step.emit("copy", "running")
            session = SessionManager()
            session.start_session(
                case_number=self._case_name,
                description=self._case_name,
                responsible_technician=self._responsible,
            )
            originals = [Path(session.add_evidence(f).file_path) for f in self._files]
            case_dir = session.session_path.parent
            self.step.emit("copy", "completed")

            pipeline = PreservationPipeline()
            pipeline.set_progress_callback(lambda name, status, _pct: self.step.emit(name, status.value))
            result = pipeline.execute(
                originals,
                case_number=self._case_name,
                responsible_technician=self._responsible,
                output_dir=case_dir / "relatorio",
                case_dir=case_dir,
                session_code=session.session.session_code,
                timestamp=self._timestamp,
                received_via=self._received_via,
                period=self._period,
                discard_outside_period=self._discard,
            )
            _write_case_summary(case_dir, self._case_name, result)
            self.finished_ok.emit(result, case_dir)
        except Exception as exc:
            logger.exception("Falha na preservacao")
            self.failed.emit(str(exc))


def _write_case_summary(case_dir: Path, case_name: str, result: Any) -> None:
    """Resumo usado pela lista de casos recentes."""
    seal = result.seal
    summary = {
        "name": case_name,
        "created_at": result.start_time.isoformat(),
        "report": str(result.report_path) if result.report_path else "",
        "timestamped": bool(seal and seal.timestamp),
        "prints": len(result.screenshot_checks),
        "prints_ok": sum(1 for c in result.screenshot_checks if c.all_ok),
    }
    (case_dir / "resumo.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def recent_cases(limit: int = 6) -> list[dict[str, Any]]:
    cases = []
    for summary in Paths.cases_dir().glob("*/resumo.json"):
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
            data["dir"] = str(summary.parent)
            cases.append(data)
        except Exception:
            continue
    cases.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    return cases[:limit]


# ---------------------------------------------------------------------- #
# Tela 1: nova preservacao
# ---------------------------------------------------------------------- #


class DropZone(QFrame):
    """Area para arrastar arquivos ou pastas."""

    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Arraste aqui os prints, o e-mail (.eml) ou o ZIP da conversa")
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        hint = QLabel("ou uma pasta com eles")
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        self.choose_button = QPushButton("Escolher arquivos…")
        self.choose_button.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.choose_button)
        row.addStretch()
        layout.addLayout(row)

    def _set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_active(True)

    def dragLeaveEvent(self, event: Any) -> None:  # noqa: N802
        self._set_active(False)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._set_active(False)
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        self.files_dropped.emit(paths)


class FileRow(QWidget):
    """Linha da lista de arquivos: tipo, nome, detalhe e botao remover."""

    removed = Signal(object)

    ICONS = {KIND_EXPORT: "💬", KIND_SCREENSHOT: "🖼️", KIND_EMAIL: "✉️"}

    def __init__(self, info: FileInfo) -> None:
        super().__init__()
        self.info = info
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        icon = QLabel(self.ICONS.get(info.kind, "📄"))
        icon.setFont(QFont(icon.font().family(), 16))
        layout.addWidget(icon)
        text = QVBoxLayout()
        text.setSpacing(1)
        text.addWidget(_label(f"<b>{info.title}</b> · {info.path.name}", wrap=False))
        detail = _label(info.detail, "muted")
        text.addWidget(detail)
        for w in info.warnings:
            text.addWidget(_label("⚠ " + w, "warning"))
        layout.addLayout(text, 1)
        remove = QPushButton("✕")
        remove.setObjectName("remove")
        remove.setToolTip("Remover da lista")
        remove.clicked.connect(lambda: self.removed.emit(self.info.path))
        layout.addWidget(remove, 0, Qt.AlignmentFlag.AlignTop)


class SetupPage(QWidget):
    start_requested = Signal(list, str, str, str, bool, object)  # ..., {period, discard}

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self._infos: dict[Path, FileInfo] = {}
        self._period_available = False
        self._settings = QSettings("LexProof", "LexProof")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        body.setObjectName("page")
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(40, 28, 40, 28)
        layout.setSpacing(16)

        layout.addWidget(_label("Nova preservação", "pageTitle"))
        layout.addWidget(_label(
            "O LexProof guarda uma cópia dos arquivos, registra a impressão digital de cada um, "
            "pede um carimbo de tempo e confere os prints com a conversa exportada. "
            "Os arquivos originais não são alterados.",
            "muted",
        ))

        # 1. Caso
        card, c = _card()
        c.addWidget(_label("1. Identifique o caso", "cardTitle"))
        c.addWidget(_label("Nome do caso", wrap=False))
        self.case_name = QLineEdit()
        self.case_name.setPlaceholderText("Ex.: Processo 1234567-89.2026 – Maria x João")
        c.addWidget(self.case_name)
        c.addWidget(_label("Responsável pela preservação", wrap=False))
        self.responsible = QLineEdit(str(self._settings.value("responsible", "")))
        self.responsible.setPlaceholderText("Seu nome")
        c.addWidget(self.responsible)
        c.addWidget(_label("Como os arquivos chegaram até você", wrap=False))
        self.received = QComboBox()
        self.received.addItems(RECEIVED_OPTIONS)
        c.addWidget(self.received)
        layout.addWidget(card)

        # 2. Arquivos
        card, c = _card()
        head = QHBoxLayout()
        head.addWidget(_label("2. Adicione os arquivos", "cardTitle", wrap=False))
        head.addStretch()
        howto = QPushButton("Como exportar a conversa do WhatsApp?")
        howto.setObjectName("link")
        howto.setCursor(Qt.CursorShape.PointingHandCursor)
        howto.clicked.connect(self._show_howto)
        head.addWidget(howto)
        c.addLayout(head)
        self.drop = DropZone()
        self.drop.files_dropped.connect(self.add_paths)
        self.drop.choose_button.clicked.connect(self._choose_files)
        c.addWidget(self.drop)
        self.file_list = QListWidget()
        self.file_list.setVisible(False)
        self.file_list.setSpacing(2)
        c.addWidget(self.file_list)
        self.set_warnings = _label("", "warning")
        self.set_warnings.setVisible(False)
        c.addWidget(self.set_warnings)
        layout.addWidget(card)

        # Periodo de interesse (so com conversa exportada)
        self.period_card, c = _card()
        c.addWidget(_label("Período de interesse", "cardTitle"))
        c.addWidget(_label(
            "Se só um trecho da conversa importa, limite o relatório a ele. As mensagens fora "
            "do período não aparecem no relatório.", "muted",
        ))
        self.period_all = QRadioButton("Toda a conversa")
        self.period_some = QRadioButton("Só o período:")
        self.period_all.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.period_all)
        group.addButton(self.period_some)
        row = QHBoxLayout()
        row.addWidget(self.period_some)
        self.period_from = QDateEdit()
        self.period_to = QDateEdit()
        for edit in (self.period_from, self.period_to):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("dd/MM/yyyy")
        row.addWidget(QLabel("de"))
        row.addWidget(self.period_from)
        row.addWidget(QLabel("até"))
        row.addWidget(self.period_to)
        row.addStretch()
        c.addWidget(self.period_all)
        c.addLayout(row)
        self.period_options = QWidget()
        opt = QVBoxLayout(self.period_options)
        opt.setContentsMargins(24, 4, 0, 0)
        self.keep_full = QRadioButton(
            "Guardar a conversa completa lacrada na pasta do caso (recomendado)"
        )
        self.discard_rest = QRadioButton(
            "Apagar o restante da conversa e guardar só o hash do arquivo completo"
        )
        self.keep_full.setChecked(True)
        fate = QButtonGroup(self)
        fate.addButton(self.keep_full)
        fate.addButton(self.discard_rest)
        opt.addWidget(self.keep_full)
        opt.addWidget(self.discard_rest)
        self.discard_hint = _label(
            "⚠ Se a outra parte contestar o recorte, a conferência vai depender de o cliente "
            "ainda ter a conversa no celular ou o arquivo exportado. O arquivo que você "
            "escolheu no computador não é apagado.", "warning",
        )
        opt.addWidget(self.discard_hint)
        c.addWidget(self.period_options)
        self.period_some.toggled.connect(self._refresh_period)
        self.discard_rest.toggled.connect(self._refresh_period)
        self.period_from.dateChanged.connect(self._refresh_state)
        self.period_to.dateChanged.connect(self._refresh_state)
        self.period_card.setVisible(False)
        layout.addWidget(self.period_card)

        # 3. Preservar
        card, c = _card()
        c.addWidget(_label("3. Preserve", "cardTitle"))
        self.timestamp = QCheckBox(
            "Registrar carimbo de tempo da FreeTSA (requer internet; só o hash é enviado)"
        )
        self.timestamp.setChecked(True)
        c.addWidget(self.timestamp)
        row = QHBoxLayout()
        self.missing = _label("", "muted", wrap=False)
        row.addWidget(self.missing)
        row.addStretch()
        self.start_button = QPushButton("Preservar e gerar relatório")
        self.start_button.setObjectName("primary")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self._start)
        row.addWidget(self.start_button)
        c.addLayout(row)
        layout.addWidget(card)

        # Casos recentes
        self.recent_box = QWidget()
        recent_layout = QVBoxLayout(self.recent_box)
        recent_layout.setContentsMargins(0, 8, 0, 0)
        recent_layout.addWidget(_label("Casos recentes", "cardTitle"))
        self.recent_list = QVBoxLayout()
        recent_layout.addLayout(self.recent_list)
        layout.addWidget(self.recent_box)
        layout.addStretch()

        self.case_name.textChanged.connect(self._refresh_state)
        self.refresh_recent()
        self._refresh_state()

    # -- arquivos ------------------------------------------------------- #

    def _choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Escolher arquivos", str(Path.home()),
            "Conversa, prints e e-mails (*.zip *.txt *.eml *.jpg *.jpeg *.png *.webp *.heic);;Todos os arquivos (*)",
        )
        self.add_paths([Path(f) for f in files])

    def add_paths(self, paths: list[Path]) -> None:
        expanded: list[Path] = []
        for p in paths:
            if p.is_dir():
                expanded += sorted(f for f in p.iterdir() if f.is_file() and not f.name.startswith("."))
            elif p.is_file():
                expanded.append(p)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for p in expanded:
                key = p.resolve()
                if key not in self._infos:
                    self._infos[key] = describe_file(p)
        finally:
            QApplication.restoreOverrideCursor()
        if not self.case_name.text().strip():
            export = next((i for i in self._infos.values() if i.kind == KIND_EXPORT), None)
            if export is not None:
                name = export.path.stem.replace("Conversa do WhatsApp com ", "Conversa com ")
                self.case_name.setText(name)
        self._rebuild_list()

    def _remove(self, path: Path) -> None:
        self._infos.pop(Path(path).resolve(), None)
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        self.file_list.clear()
        order = {KIND_EMAIL: 0, KIND_EXPORT: 1, KIND_SCREENSHOT: 2}
        for info in sorted(self._infos.values(), key=lambda i: (order.get(i.kind, 2), i.path.name)):
            row = FileRow(info)
            row.removed.connect(self._remove)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, row)
        self.file_list.setVisible(bool(self._infos))
        self.file_list.setFixedHeight(min(320, sum(
            self.file_list.sizeHintForRow(i) + 4 for i in range(self.file_list.count())
        ) + 8))
        warnings = intake_warnings(list(self._infos.values()))
        self.set_warnings.setText("\n".join("⚠ " + w for w in warnings))
        self.set_warnings.setVisible(bool(warnings))
        export = next((i for i in self._infos.values() if i.kind == KIND_EXPORT and i.first_date), None)
        self._period_available = export is not None
        self.period_card.setVisible(self._period_available)
        if export is not None:
            first = QDate(export.first_date.year, export.first_date.month, export.first_date.day)
            last = QDate(export.last_date.year, export.last_date.month, export.last_date.day)
            for edit in (self.period_from, self.period_to):
                edit.setDateRange(first, last)
            self.period_from.setDate(first)
            self.period_to.setDate(last)
        else:
            self.period_all.setChecked(True)
        self._refresh_period()

    def _refresh_period(self) -> None:
        some = self.period_some.isChecked()
        self.period_from.setEnabled(some)
        self.period_to.setEnabled(some)
        self.period_options.setVisible(some)
        self.discard_hint.setVisible(some and self.discard_rest.isChecked())
        self._refresh_state()

    def period_choice(self) -> dict[str, Any]:
        if not self._period_available or not self.period_some.isChecked():
            return {"period": None, "discard": False}
        start = self.period_from.date().toPython()
        end = self.period_to.date().toPython()
        return {"period": (start, end), "discard": self.discard_rest.isChecked()}

    def _refresh_state(self) -> None:
        missing = []
        if not self.case_name.text().strip():
            missing.append("o nome do caso")
        if not self._infos:
            missing.append("os arquivos")
        if self.period_some.isChecked() and self.period_from.date() > self.period_to.date():
            missing.append("um período válido")
        self.start_button.setEnabled(not missing)
        self.missing.setText(f"Falta: {' e '.join(missing)}" if missing else "")

    # -- acoes ---------------------------------------------------------- #

    def _start(self) -> None:
        responsible = self.responsible.text().strip()
        self._settings.setValue("responsible", responsible)
        self.start_requested.emit(
            [i.path for i in self._infos.values()],
            self.case_name.text().strip(),
            responsible,
            self.received.currentText(),
            self.timestamp.isChecked(),
            self.period_choice(),
        )

    def reset(self) -> None:
        self._infos.clear()
        self.case_name.clear()
        self.received.setCurrentIndex(0)
        self.period_all.setChecked(True)
        self.keep_full.setChecked(True)
        self._rebuild_list()
        self.refresh_recent()

    def refresh_recent(self) -> None:
        while self.recent_list.count():
            item = self.recent_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cases = recent_cases()
        self.recent_box.setVisible(bool(cases))
        for case in cases:
            row = QHBoxLayout()
            status = "carimbado" if case.get("timestamped") else "sem carimbo"
            prints = case.get("prints", 0)
            if prints:
                status += f" · {case.get('prints_ok', 0)} de {prints} print(s) sem divergência"
            when = case.get("created_at", "")[:10]
            if when:
                when = f"{when[8:10]}/{when[5:7]}/{when[0:4]}"
            row.addWidget(_label(f"<b>{case.get('name', '-')}</b>  <span style='color:{MUTED}'>{when} · {status}</span>"), 1)
            if case.get("report") and Path(case["report"]).exists():
                btn = QPushButton("Abrir relatório")
                btn.clicked.connect(lambda _=False, p=case["report"]: _open_path(Path(p)))
                row.addWidget(btn)
            folder = QPushButton("Pasta")
            folder.clicked.connect(lambda _=False, p=case["dir"]: _open_path(Path(p)))
            row.addWidget(folder)
            holder = QWidget()
            holder.setLayout(row)
            self.recent_list.addWidget(holder)

    def _show_howto(self) -> None:
        HowToDialog(self).exec()


class HowToDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Como exportar a conversa")
        self.resize(560, 520)
        layout = QVBoxLayout(self)
        text = QTextBrowser()
        text.setOpenExternalLinks(True)
        text.setHtml("""
        <h3>No Android</h3>
        <ol>
          <li>Abra a conversa no WhatsApp.</li>
          <li>Toque em <b>⋮</b> (canto superior direito) → <b>Mais</b> → <b>Exportar conversa</b>.</li>
          <li>Escolha <b>Sem mídia</b> (mais rápido) ou <b>Incluir mídia</b>.</li>
          <li>Salve o arquivo .zip no Google Drive, envie por e-mail para você mesmo
              ou copie pelo cabo USB.</li>
        </ol>
        <h3>No iPhone</h3>
        <ol>
          <li>Abra a conversa e toque no <b>nome do contato</b>, no topo.</li>
          <li>Role até o fim e toque em <b>Exportar conversa</b>.</li>
          <li>Escolha com ou sem mídia e toque em <b>Salvar em Arquivos</b> ou envie por e-mail.</li>
        </ol>
        <h3>Prints</h3>
        <p>Tire os prints no próprio celular e copie <b>os arquivos originais</b>
        para o computador (cabo, Drive, ou e-mail como anexo).</p>
        <p style="color:#b26a00"><b>Não envie os prints pelo WhatsApp como foto:</b> o WhatsApp
        recomprime a imagem, troca o nome do arquivo e apaga a data em que o print foi
        tirado. Se precisar usar o WhatsApp, envie como <b>Documento</b>.</p>
        <h3>Se os arquivos vierem de um cliente: por e-mail</h3>
        <p>O e-mail é a melhor forma: o provedor do cliente (Gmail, Outlook) assina a mensagem
        com os anexos, e o LexProof confere essa assinatura.</p>
        <p><b>Peça ao cliente:</b></p>
        <ol>
          <li>Abrir o app do Gmail (ou outro e-mail) <b>no celular</b> e criar uma mensagem para você.</li>
          <li>Tocar no clipe → <b>Anexar arquivo</b> e escolher os prints na galeria.</li>
          <li>Mandar <b>no máximo uns 20 prints por e-mail</b>. Acima de 25 MB o Gmail troca os
              anexos por um link do Drive, que não fica coberto pela assinatura.</li>
        </ol>
        <p>A exportação da conversa não é obrigatória: sem ela, o LexProof confere os prints
        entre si (lacunas e contradições).</p>
        <p><b>Você, ao receber (Gmail no computador):</b> abra o e-mail → <b>⋮</b> →
        <b>Mostrar original</b> → <b>Baixar original</b>. Arraste o arquivo .eml para o
        LexProof. Não encaminhe o e-mail antes: o encaminhamento perde a assinatura do cliente.
        Faça isso logo, porque os provedores trocam as chaves de assinatura de tempos em tempos.</p>
        """)
        layout.addWidget(text)
        close = QPushButton("Entendi")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)


# ---------------------------------------------------------------------- #
# Tela 2: progresso
# ---------------------------------------------------------------------- #


class ProgressPage(QWidget):
    MARKS = {"pending": ("○", MUTED), "running": ("●", PRIMARY), "completed": ("✓", SUCCESS),
             "skipped": ("–", MUTED), "failed": ("!", WARNING)}

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 28, 40, 28)
        layout.setSpacing(14)
        self.title = _label("Preservando…", "pageTitle")
        layout.addWidget(self.title)
        self.subtitle = _label("", "muted")
        layout.addWidget(self.subtitle)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, len(VISIBLE_STEPS))
        layout.addWidget(self.bar)
        card, c = _card()
        self._rows: dict[str, tuple[QLabel, QLabel]] = {}
        for key, text in VISIBLE_STEPS:
            row = QHBoxLayout()
            mark = QLabel()
            mark.setFixedWidth(22)
            mark.setFont(QFont(mark.font().family(), 13, QFont.Weight.Bold))
            label = QLabel(text)
            row.addWidget(mark)
            row.addWidget(label, 1)
            c.addLayout(row)
            self._rows[key] = (mark, label)
        layout.addWidget(card)
        layout.addStretch()

    def start(self, case_name: str) -> None:
        self.subtitle.setText(f"Caso: {case_name}. Isso leva menos de um minuto.")
        self.bar.setValue(0)
        for key in self._rows:
            self.set_status(key, "pending")

    def set_status(self, key: str, status: str) -> None:
        if key not in self._rows:
            return
        mark, label = self._rows[key]
        symbol, color = self.MARKS.get(status, self.MARKS["pending"])
        mark.setText(symbol)
        mark.setStyleSheet(f"color: {color};")
        label.setStyleSheet("font-weight: 600;" if status == "running" else "")
        done = sum(1 for k in self._rows if self._rows[k][0].text() in ("✓", "–", "!"))
        self.bar.setValue(done)


# ---------------------------------------------------------------------- #
# Tela 3: resultado
# ---------------------------------------------------------------------- #


class ResultPage(QWidget):
    new_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self._report: Optional[Path] = None
        self._case_dir: Optional[Path] = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        body.setObjectName("page")
        scroll.setWidget(body)
        self.layout_ = QVBoxLayout(body)
        self.layout_.setContentsMargins(40, 28, 40, 28)
        self.layout_.setSpacing(14)

        self.banner = QFrame()
        self.banner.setObjectName("banner")
        b = QVBoxLayout(self.banner)
        b.setContentsMargins(20, 16, 20, 16)
        self.banner_title = _label("", "pageTitle")
        self.banner_text = _label("")
        b.addWidget(self.banner_title)
        b.addWidget(self.banner_text)
        self.layout_.addWidget(self.banner)

        actions = QHBoxLayout()
        self.open_report = QPushButton("Abrir relatório (PDF)")
        self.open_report.setObjectName("primary")
        self.open_report.clicked.connect(lambda: self._report and _open_path(self._report))
        self.open_folder = QPushButton("Abrir pasta do caso")
        self.open_folder.clicked.connect(lambda: self._case_dir and _open_path(self._case_dir))
        again = QPushButton("Nova preservação")
        again.clicked.connect(self.new_requested.emit)
        actions.addWidget(self.open_report)
        actions.addWidget(self.open_folder)
        actions.addStretch()
        actions.addWidget(again)
        self.layout_.addLayout(actions)

        self.cards = QVBoxLayout()
        self.cards.setSpacing(12)
        self.layout_.addLayout(self.cards)

        self.layout_.addWidget(_label("Conferência dos prints", "cardTitle"))
        self.prints_hint = _label("", "muted")
        self.layout_.addWidget(self.prints_hint)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Print / mensagem", "Data", "Hora", "Resultado"])
        self.tree.setColumnWidth(0, 520)
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(2, 55)
        self.tree.setMinimumHeight(260)
        self.tree.setAlternatingRowColors(True)
        self.layout_.addWidget(self.tree)
        self.layout_.addStretch()

    def show_result(self, result: Any, case_dir: Path) -> None:
        self._report = result.report_path
        self._case_dir = case_dir
        self.open_report.setEnabled(bool(result.report_path))

        seal = result.seal
        checks = result.screenshot_checks
        stitch = result.stitch
        problems = [c for c in checks if not c.all_ok]
        if stitch is not None and stitch.order and stitch.needs_attention(bool(checks)):
            problems.append(stitch)
        problems += [e for e in result.emails if not e.verified]
        stamped = bool(seal and seal.timestamp)
        if not problems and stamped:
            self._set_banner(SUCCESS, "#e8f5e9", "Preservação concluída",
                             "Os arquivos foram guardados e carimbados, e o relatório está pronto.")
        elif problems:
            self._set_banner(DANGER, "#fdecea", "Concluída: há pontos a examinar",
                             "Veja abaixo as divergências, lacunas ou assinaturas não confirmadas "
                             "antes de usar esses prints.")
        else:
            self._set_banner(WARNING, "#fff4e5", "Concluída sem carimbo de tempo",
                             "Os arquivos foram guardados e o relatório gerado, mas o carimbo de "
                             "tempo não foi obtido.")

        while self.cards.count():
            item = self.cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if stamped:
            from lexproof.reports.pdf_report import _fmt_local

            when = _fmt_local(seal.timestamp.gen_time).split(" = ")[0]
            self._add_card("🕒  Carimbo de tempo",
                           f"<b>{when}</b>, emitido por {seal.timestamp.tsa_url}. "
                           f"Qualquer pessoa pode conferir com os arquivos da pasta "
                           f"<i>preservacao</i> do caso.")
        else:
            reason = seal.timestamp_error if seal and seal.timestamp_error else "desativado"
            self._add_card("🕒  Carimbo de tempo",
                           f"<span style='color:{WARNING}'><b>Não obtido</b> ({reason}).</span> "
                           f"Sem ele, a data desta preservação não fica atestada por terceiro.")

        for em in result.emails:
            if em.verified:
                self._add_card("✉️  E-mail recebido",
                               f"De <b>{html.escape(em.sender)}</b>"
                               + (f" em {em.date:%d/%m/%Y às %H:%M}" if em.date else "")
                               + f", com {len(em.attachments)} anexo(s). <span style='color:{SUCCESS}'>"
                               f"<b>Assinatura do provedor válida</b> ({em.aligned_signature.domain})</span>: "
                               f"os anexos são exatamente os que saíram da conta do remetente.")
            else:
                reason = em.signatures[0].error if em.signatures else "sem assinatura DKIM"
                self._add_card("✉️  E-mail recebido",
                               f"{html.escape(em.eml_path.name)}: <span style='color:{DANGER}'><b>assinatura do "
                               f"provedor não confirmada</b> ({html.escape(reason)})</span>. O e-mail não comprova "
                               f"a origem dos anexos.")

        ex = result.excerpt
        if ex is not None:
            fate = ("o restante foi <b>apagado</b> da pasta do caso (ficou só o hash do arquivo completo)"
                    if ex.discarded else "a conversa completa ficou guardada, lacrada, fora do relatório")
            self._add_card("✂️  Recorte do período",
                           f"Relatório limitado a <b>{ex.start:%d/%m/%Y} a {ex.end:%d/%m/%Y}</b>: "
                           f"{ex.kept_messages} de {ex.total_messages} mensagens; {fate}. "
                           f"O recorte pode ser conferido contra o arquivo completo.")

        msgs = result.messages
        if msgs:
            from lexproof.reports.pdf_report import _safe

            people = sorted({_safe(m.sender).replace("[emoji]", "").strip()
                             for m in msgs if m.sender and m.sender != "Desconhecido"})
            self._add_card("💬  Conversa exportada",
                           f"<b>{len(msgs)} mensagens</b>, de {msgs[0].timestamp:%d/%m/%Y} a "
                           f"{msgs[-1].timestamp:%d/%m/%Y}, entre {' e '.join(people)}.")
        elif not (stitch and stitch.order):
            self._add_card("💬  Conversa exportada",
                           f"<span style='color:{WARNING}'>Nenhuma conversa do WhatsApp foi encontrada "
                           f"nos arquivos.</span>")

        if stitch is not None and stitch.order:
            first, last = stitch.first, stitch.last
            span = f", de {first.when} a {last.when}" if first and last else ""
            attention = stitch.needs_attention(bool(checks))
            color = DANGER if attention else SUCCESS
            if stitch.all_ok:
                detail = "se encadeiam sem lacunas nem contradições"
            elif not attention:
                detail = (f"sem contradições; {len(stitch.gaps)} trecho(s) não printado(s) entre "
                          f"eles, o que é normal quando cada print é conferido com a conversa")
            else:
                detail = (f"{len(stitch.gaps)} lacuna(s), {len(stitch.contradictions)} contradição(ões) "
                          f"e {len(stitch.issues)} incoerência(s)")
            self._add_card("🧩  Prints entre si",
                           f"{len(stitch.order)} print(s), {len(stitch.messages)} mensagens distintas{span}: "
                           f"<span style='color:{color}'><b>{detail}</b></span>.")

        total = sum(c.total for c in checks)
        confirmed = sum(c.confirmed for c in checks)
        if checks:
            color = SUCCESS if all(c.all_ok for c in checks) else DANGER
            self._add_card("🖼️  Prints",
                           f"<span style='color:{color}'><b>{confirmed} de {total}</b> mensagens "
                           f"visíveis conferem</span> com a conversa, em {len(checks)} print(s).")
        self._fill_tree(checks, stitch)

    def _set_banner(self, color: str, bg: str, title: str, text: str) -> None:
        self.banner.setStyleSheet(f"QFrame#banner {{ background: {bg}; border: 1px solid {color}; }}")
        self.banner_title.setStyleSheet(f"color: {color};")
        self.banner_title.setText(title)
        self.banner_text.setText(text)

    def _add_card(self, title: str, html: str) -> None:
        card, c = _card()
        c.addWidget(_label(title, "cardTitle"))
        c.addWidget(_label(html))
        self.cards.addWidget(card)

    def _fill_tree(self, checks: list[Any], stitch: Any = None) -> None:
        from lexproof.reports.pdf_report import _safe

        self.tree.clear()
        has_stitch = stitch is not None and bool(stitch.order)
        if not checks and not has_stitch:
            self.prints_hint.setText("Nenhum print de conversa foi conferido.")
            self.tree.setVisible(False)
            return
        self.tree.setVisible(True)
        self.prints_hint.setText("Clique em um item para ver os detalhes da conferência.")
        if has_stitch:
            self._add_stitch_items(stitch, with_export=bool(checks))
        for chk in checks:
            ok = chk.all_ok
            top = QTreeWidgetItem([
                chk.reading.path.name, "", "",
                f"{chk.confirmed} de {chk.total} conferem" + ("" if ok else " · ver detalhes"),
            ])
            top.setForeground(3, QColor(SUCCESS if ok else DANGER))
            font = top.font(0)
            font.setBold(True)
            top.setFont(0, font)
            self.tree.addTopLevelItem(top)
            extra = []
            if chk.contact_matches is False:
                extra.append(f"Contato do print ({chk.reading.contact}) diferente da conversa ({chk.export_contact})")
            if chk.captured_after_messages is False:
                extra.append("O print é anterior a mensagens que ele mostra")
            if not chk.order_ok:
                extra.append("As mensagens aparecem em ordem diferente da exportação")
            for m in chk.hidden_messages:
                extra.append(f"Mensagem omitida no print: {m.timestamp:%d/%m/%Y %H:%M} \"{_safe(m.content)[:60]}\"")
            for e in extra:
                item = QTreeWidgetItem(["⚠ " + e, "", "", "Atenção"])
                item.setForeground(0, QColor(DANGER))
                item.setForeground(3, QColor(DANGER))
                top.addChild(item)
            for c in chk.checks:
                b = c.bubble
                item = QTreeWidgetItem([
                    _safe(b.text)[:80],
                    b.date.strftime("%d/%m/%Y") if b.date else "—",
                    b.time or "?",
                    c.status.label,
                ])
                item.setForeground(3, QColor(SUCCESS if c.status.ok else DANGER))
                if c.notes:
                    item.setToolTip(0, "\n".join(c.notes))
                    item.setToolTip(3, "\n".join(c.notes))
                    for note in c.notes:
                        child = QTreeWidgetItem(["   " + _safe(note), "", "", ""])
                        child.setForeground(0, QColor(MUTED))
                        item.addChild(child)
                top.addChild(item)
            top.setExpanded(not ok)
            if not ok:
                for i in range(top.childCount()):
                    top.child(i).setExpanded(True)

    def _add_stitch_items(self, st: Any, with_export: bool = False) -> None:
        from lexproof.reports.pdf_report import _safe

        ok = not st.needs_attention(with_export)
        top = QTreeWidgetItem([
            "Prints conferidos entre si", "", "",
            ("sem lacunas nem contradições" if st.all_ok else "sem contradições") if ok else "ver detalhes",
        ])
        top.setForeground(3, QColor(SUCCESS if ok else DANGER))
        font = top.font(0)
        font.setBold(True)
        top.setFont(0, font)
        self.tree.addTopLevelItem(top)
        gap_after = {g.after_print for g in st.gaps}
        for c in st.contradictions:
            diffs = "; ".join(f"\"{a}\" x \"{b}\"" for a, b in c.differences)
            item = QTreeWidgetItem([f"⚠ Mesma mensagem com textos diferentes: {diffs}", "", "", "Contradição"])
            item.setForeground(0, QColor(DANGER))
            item.setForeground(3, QColor(DANGER))
            item.setToolTip(0, f"{c.print_a}: {_safe(c.text_a)}\n{c.print_b}: {_safe(c.text_b)}")
            for name, text in ((c.print_a, c.text_a), (c.print_b, c.text_b)):
                child = QTreeWidgetItem([f"   {name}: {_safe(text)[:70]}", "", "", ""])
                child.setForeground(0, QColor(MUTED))
                item.addChild(child)
            top.addChild(item)
        for i in st.issues:
            item = QTreeWidgetItem([f"⚠ {i.message}", "", "", "Atenção"])
            item.setForeground(0, QColor(DANGER))
            item.setForeground(3, QColor(DANGER))
            item.setToolTip(0, f"{i.print_name}: {i.message}")
            child = QTreeWidgetItem([f"   {i.print_name}", "", "", ""])
            child.setForeground(0, QColor(MUTED))
            item.addChild(child)
            top.addChild(item)
        for r in st.order:
            own = [m for m in st.messages if r.path.name in m.sources]
            gap = r.path.name in gap_after
            item = QTreeWidgetItem([
                r.path.name,
                own[0].when.split(" ")[0] if own else "",
                own[0].when.split(" ")[-1] if own else "",
                ("trecho não printado antes" if with_export else "⚠ lacuna antes deste print")
                if gap else "continua",
            ])
            item.setForeground(3, QColor(DANGER if gap and not with_export else MUTED))
            if gap:
                g = next(g for g in st.gaps if g.after_print == r.path.name)
                child = QTreeWidgetItem([
                    f"   Pode haver mensagens não capturadas entre {g.last_before.when} e {g.first_after.when}",
                    "", "", "",
                ])
                child.setForeground(0, QColor(MUTED if with_export else DANGER))
                item.addChild(child)
            for m in own:
                child = QTreeWidgetItem([
                    "   " + ("(ligação)" if m.kind == "call" else _safe(m.text)[:80]),
                    m.date.strftime("%d/%m/%Y") if m.date else "—", m.time or "?",
                    f"em {len(m.sources)} print(s)",
                ])
                child.setForeground(3, QColor(MUTED))
                item.addChild(child)
            top.addChild(item)
        top.setExpanded(True)
        # setExpanded so tem efeito depois que o item esta na arvore
        for i in range(top.childCount()):
            child = top.child(i)
            if child.foreground(3).color() == QColor(DANGER):
                child.setExpanded(True)


# ---------------------------------------------------------------------- #
# Janela
# ---------------------------------------------------------------------- #


class SimpleMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LexProof — Preservação de conversas")
        self.resize(980, 820)
        self._worker: Optional[PreservationWorker] = None

        central = QWidget()
        central.setObjectName("page")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("header")
        h = QHBoxLayout(header)
        h.setContentsMargins(40, 14, 40, 14)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(_label("LexProof", "appTitle", wrap=False))
        titles.addWidget(_label("Relatório de Preservação e Integridade de conversas do WhatsApp", "appSubtitle", wrap=False))
        h.addLayout(titles)
        h.addStretch()
        cases = QPushButton("Pasta dos casos")
        cases.clicked.connect(lambda: _open_path(Paths.cases_dir()))
        h.addWidget(cases)
        root.addWidget(header)

        self.stack = QStackedWidget()
        self.setup = SetupPage()
        self.progress = ProgressPage()
        self.result = ResultPage()
        for page in (self.setup, self.progress, self.result):
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.setup.start_requested.connect(self._start)
        self.result.new_requested.connect(self._new)

    def _start(self, files: list[Path], case_name: str, responsible: str,
               received_via: str, timestamp: bool, options: dict[str, Any]) -> None:
        self.progress.start(case_name)
        if not timestamp:
            self.progress.set_status("Carimbo de tempo", "skipped")
        if not options.get("period"):
            self.progress.set_status("Recorte do período", "skipped")
        self.stack.setCurrentWidget(self.progress)
        self._worker = PreservationWorker(
            files, case_name, responsible, received_via, timestamp,
            period=options.get("period"), discard=options.get("discard", False),
        )
        if timestamp:
            self._worker.step.connect(self.progress.set_status)
        else:
            self._worker.step.connect(
                lambda key, status: key != "Carimbo de tempo" and self.progress.set_status(key, status)
            )
        self._worker.finished_ok.connect(self._done)
        self._worker.failed.connect(self._failed)
        self._worker.start()

    def _done(self, result: Any, case_dir: Path) -> None:
        self.result.show_result(result, case_dir)
        self.stack.setCurrentWidget(self.result)

    def _failed(self, message: str) -> None:
        QMessageBox.critical(
            self, "Não foi possível concluir",
            f"A preservação foi interrompida:\n\n{message}\n\nOs arquivos originais não foram alterados.",
        )
        self.stack.setCurrentWidget(self.setup)

    def _new(self) -> None:
        self.setup.reset()
        self.stack.setCurrentWidget(self.setup)


def apply_light_theme(app: QApplication) -> None:
    """Tema claro fixo, independente do tema do sistema."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("white"))
    palette.setColor(QPalette.ColorRole.Base, QColor("white"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.Button, QColor("white"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#c5cae9"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("white"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#202124"))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
