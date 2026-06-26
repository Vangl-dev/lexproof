"""Gerador de relatórios em formato HTML."""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jinja2

from lexproof import __version__
from lexproof.models.report import ReportConfig
from lexproof.reports.base import BaseReportGenerator
from lexproof.reports.qr_generator import QRCodeGenerator

logger = logging.getLogger("lexproof.reports.html")

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LexProof - {{ metadata.get('title', 'Relatório') }}</title>
    <style>
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-tertiary: #e9ecef;
            --text-primary: #1a1a2e;
            --text-secondary: #495057;
            --accent: #16213e;
            --accent-light: #0f3460;
            --border: #dee2e6;
            --success: #28a745;
            --danger: #dc3545;
            --warning: #ffc107;
            --code-bg: #f4f4f4;
        }
        [data-theme="dark"] {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-tertiary: #0f3460;
            --text-primary: #e0e0e0;
            --text-secondary: #b0b0b0;
            --accent: #4a90d9;
            --accent-light: #6bb3ff;
            --border: #333355;
            --success: #4caf50;
            --danger: #f44336;
            --warning: #ff9800;
            --code-bg: #2a2a4a;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        header {
            background: var(--accent);
            color: white;
            padding: 3rem 2rem;
            text-align: center;
        }
        header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        header .subtitle { font-size: 1.1rem; opacity: 0.9; }
        header .meta { margin-top: 1.5rem; font-size: 0.9rem; opacity: 0.8; }
        .section {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin: 1.5rem 0;
            overflow: hidden;
        }
        .section-header {
            background: var(--accent);
            color: white;
            padding: 1rem 1.5rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
        }
        .section-header:hover { background: var(--accent-light); }
        .section-header .toggle { font-size: 1.2rem; transition: transform 0.3s; }
        .section-header.collapsed .toggle { transform: rotate(-90deg); }
        .section-body { padding: 1.5rem; }
        .section-body.collapsed { display: none; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        th, td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        th {
            background: var(--accent);
            color: white;
            font-weight: 600;
        }
        tr:nth-child(even) { background: var(--bg-tertiary); }
        tr:hover { background: var(--accent); color: white; }
        .hash-value {
            font-family: 'Courier New', monospace;
            font-size: 0.75rem;
            word-break: break-all;
            background: var(--code-bg);
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
        }
        .status-badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-pass { background: var(--success); color: white; }
        .status-fail { background: var(--danger); color: white; }
        .status-warning { background: var(--warning); color: #333; }
        .qr-section { text-align: center; padding: 2rem; }
        .qr-section img { max-width: 200px; border: 4px solid var(--border); border-radius: 8px; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .summary-card {
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
            border: 1px solid var(--border);
        }
        .summary-card .number { font-size: 2rem; font-weight: bold; color: var(--accent); }
        .summary-card .label { font-size: 0.85rem; color: var(--text-secondary); }
        .inconsistency-item {
            background: var(--bg-tertiary);
            border-left: 4px solid var(--danger);
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
            border-radius: 0 4px 4px 0;
        }
        .custody-event {
            padding: 0.5rem 0;
            border-bottom: 1px dashed var(--border);
        }
        .timeline-entry {
            display: flex;
            gap: 1rem;
            padding: 0.75rem;
            margin: 0.5rem 0;
            background: var(--bg-tertiary);
            border-radius: 4px;
        }
        .timeline-entry .ts { font-weight: 600; min-width: 150px; color: var(--accent); }
        .timeline-entry .content { flex: 1; }
        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }
        @media print {
            .section-header { cursor: default; }
            .section-body.collapsed { display: block !important; }
            .toggle { display: none; }
            body { font-size: 10pt; }
            .container { padding: 0; }
            .section { break-inside: avoid; }
        }
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            header h1 { font-size: 1.8rem; }
            .summary-grid { grid-template-columns: repeat(2, 1fr); }
            table { font-size: 0.85rem; }
            th, td { padding: 0.5rem; }
        }
    </style>
</head>
<body>
    <header>
        <h1>LEXPROOF</h1>
        <div class="subtitle">Relatório de Preservação de Evidências Digitais</div>
        <div class="meta">
            <div>{{ metadata.get('title', 'Sem título') }}</div>
            {% if metadata.get('case_number') %}<div>Processo: {{ metadata['case_number'] }}</div>{% endif %}
            {% if metadata.get('client_name') %}<div>Cliente: {{ metadata['client_name'] }}</div>{% endif %}
            {% if metadata.get('lawyer_name') %}<div>Advogado: {{ metadata['lawyer_name'] }}</div>{% endif %}
            <div>Gerado em: {{ report_generated_at }}</div>
        </div>
    </header>

    <div class="container">
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>Resumo</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="number">{{ summary.total_evidence_files }}</div>
                        <div class="label">Evidências</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{{ summary.total_hash_results }}</div>
                        <div class="label">Hashes</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{{ summary.total_timeline_entries }}</div>
                        <div class="label">Entradas Timeline</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{{ summary.verification_pass }}</div>
                        <div class="label">Verificações OK</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{{ summary.verification_fail }}</div>
                        <div class="label">Verificações Falha</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">{{ summary.total_inconsistencies }}</div>
                        <div class="label">Inconsistências</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>1. Evidências</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                {% if evidence_files %}
                <table>
                    <thead>
                        <tr><th>Arquivo</th><th>Tipo</th><th>Tamanho</th><th>Hash SHA-256</th></tr>
                    </thead>
                    <tbody>
                        {% for ev in evidence_files %}
                        <tr>
                            <td>{{ ev.file_name }}</td>
                            <td>{{ ev.evidence_type }}</td>
                            <td>{{ format_size(ev.file_size) }}</td>
                            <td><span class="hash-value">{{ ev.original_hash or 'N/A' }}</span></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p>Nenhuma evidência registrada.</p>
                {% endif %}
            </div>
        </div>

        {% if include_hashes %}
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>2. Resultados de Hash</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                {% if hash_results %}
                <table>
                    <thead>
                        <tr><th>Algoritmo</th><th>Arquivo</th><th>Hash</th><th>Data/Hora</th></tr>
                    </thead>
                    <tbody>
                        {% for hr in hash_results %}
                        <tr>
                            <td>{{ hr.algorithm }}</td>
                            <td>{{ hr.file_path }}</td>
                            <td><span class="hash-value">{{ hr.hash_value }}</span></td>
                            <td>{{ hr.computed_at }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p>Nenhum hash calculado.</p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if include_timeline %}
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>3. Linha do Tempo</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                {% if timeline %}
                {% for entry in timeline %}
                <div class="timeline-entry">
                    <span class="ts">{{ entry.timestamp }}</span>
                    <span class="content">
                        <strong>[{{ entry.entry_type }}]</strong>
                        {% if entry.sender %}{{ entry.sender }}: {% endif %}
                        {{ entry.content }}
                    </span>
                </div>
                {% endfor %}
                {% else %}
                <p>Nenhuma entrada na linha do tempo.</p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if include_ocr %}
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>4. Resultados de OCR</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                {% if ocr_results %}
                {% for ocr in ocr_results %}
                <div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--bg-tertiary); border-radius: 4px;">
                    <h4>{{ ocr.source_image }}</h4>
                    <p><strong>Confiança:</strong> {{ "%.1f"|format(ocr.confidence * 100) }}%</p>
                    <p><strong>Engine:</strong> {{ ocr.engine_used }}</p>
                    <p><strong>Tempo:</strong> {{ "%.2f"|format(ocr.processing_time) }}s</p>
                    {% if ocr.detected_timestamps %}
                    <p><strong>Timestamps:</strong> {{ ocr.detected_timestamps|join(', ') }}</p>
                    {% endif %}
                    {% if ocr.detected_senders %}
                    <p><strong>Remetentes:</strong> {{ ocr.detected_senders|join(', ') }}</p>
                    {% endif %}
                    {% if ocr.extracted_text %}
                    <details>
                        <summary>Texto Extraído</summary>
                        <pre style="white-space: pre-wrap; margin-top: 0.5rem;">{{ ocr.extracted_text }}</pre>
                    </details>
                    {% endif %}
                </div>
                {% endfor %}
                {% else %}
                <p>Nenhum resultado de OCR disponível.</p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if include_verification %}
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>5. Resultados de Verificação</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                {% if verification_results %}
                <table>
                    <thead>
                        <tr><th>Verificação</th><th>Status</th><th>Esperado</th><th>Atual</th></tr>
                    </thead>
                    <tbody>
                        {% for vr in verification_results %}
                        <tr>
                            <td>{{ vr.check_name }}</td>
                            <td><span class="status-badge status-{{ vr.status }}">{{ vr.status }}</span></td>
                            <td><span class="hash-value">{{ vr.expected or 'N/A' }}</span></td>
                            <td><span class="hash-value">{{ vr.actual or 'N/A' }}</span></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p>Nenhuma verificação realizada.</p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if include_custody %}
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>6. Cadeia de Custódia</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                {% if custody_chains %}
                {% for chain in custody_chains %}
                <h4>Evidência: {{ chain.evidence_id }}</h4>
                {% for event in chain.events %}
                <div class="custody-event">
                    <strong>{{ event.event_type }}</strong> - {{ event.description }}
                    <br><small>{{ event.timestamp }} | Operador: {{ event.operator }}</small>
                    {% if event.hash_before %}<br><small>Hash antes: <span class="hash-value">{{ event.hash_before }}</span></small>{% endif %}
                    {% if event.hash_after %}<br><small>Hash depois: <span class="hash-value">{{ event.hash_after }}</span></small>{% endif %}
                </div>
                {% endfor %}
                {% endfor %}
                {% else %}
                <p>Nenhuma cadeia de custódia registrada.</p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if inconsistencies %}
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>7. Inconsistências Detectadas</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                {% for inc in inconsistencies %}
                <div class="inconsistency-item">{{ inc }}</div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if include_qr_code and qr_code_b64 %}
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>QR Code de Verificação</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body qr-section">
                <p>Escaneie este QR code para verificar a integridade do relatório:</p>
                <br>
                <img src="data:image/png;base64,{{ qr_code_b64 }}" alt="QR Code de Verificação">
                {% if qr_hash %}
                <p style="margin-top: 1rem;"><span class="hash-value">{{ qr_hash }}</span></p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if custom_notes %}
        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <span>Notas Adicionais</span>
                <span class="toggle">&#9660;</span>
            </div>
            <div class="section-body">
                <p>{{ custom_notes }}</p>
            </div>
        </div>
        {% endif %}
    </div>

    <footer>
        LexProof v{{ app_version }} - Preservação de Evidências Digitais<br>
        Gerado em {{ report_generated_at }}
    </footer>

    <script>
        function toggleSection(header) {
            const body = header.nextElementSibling;
            const toggle = header.querySelector('.toggle');
            body.classList.toggle('collapsed');
            header.classList.toggle('collapsed');
            toggle.innerHTML = body.classList.contains('collapsed') ? '&#9654;' : '&#9660;';
        }
    </script>
</body>
</html>
"""


class HTMLReportGenerator(BaseReportGenerator):
    """Gera relatórios em formato HTML com suporte a temas e responsividade."""

    def __init__(self) -> None:
        """Inicializa o gerador HTML com o template Jinja2."""
        self.qr_generator = QRCodeGenerator()
        self.env = jinja2.Environment(autoescape=True)
        self.template = self.env.from_string(HTML_TEMPLATE)

    def generate(self, case_data: dict[str, Any], config: ReportConfig) -> Path:
        """Gera o relatório HTML.

        Args:
            case_data: Dicionário com os dados do caso.
            config: Configuração do relatório.

        Returns:
            Caminho do arquivo HTML gerado.
        """
        report_data = self.prepare_report_data(case_data)
        output_path = config.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        qr_code_b64 = ""
        qr_hash = ""
        if config.include_qr_code:
            qr_code_b64, qr_hash = self._generate_qr_base64(report_data)

        html_content = self.template.render(
            report_generated_at=report_data["report_generated_at"],
            app_version=report_data["app_version"],
            metadata=report_data.get("metadata", {}),
            summary=report_data.get("summary", {}),
            evidence_files=report_data.get("evidence_files", []),
            hash_results=report_data.get("hash_results", []),
            timeline=report_data.get("timeline", []),
            ocr_results=report_data.get("ocr_results", []),
            verification_results=report_data.get("verification_results", []),
            custody_chains=report_data.get("custody_chains", []),
            inconsistencies=report_data.get("inconsistencies", []),
            include_hashes=config.include_hashes,
            include_timeline=config.include_timeline,
            include_ocr=config.include_ocr,
            include_verification=config.include_verification,
            include_custody=config.include_custody,
            include_qr_code=config.include_qr_code,
            qr_code_b64=qr_code_b64,
            qr_hash=qr_hash,
            custom_notes=config.custom_notes,
            format_size=self._format_file_size,
        )

        output_path.write_text(html_content, encoding="utf-8")
        logger.info("Relatório HTML gerado: %s", output_path)
        return output_path

    def _generate_qr_base64(self, report_data: dict[str, Any]) -> tuple[str, str]:
        """Gera QR code e retorna como string base64.

        Args:
            report_data: Dados preparados do relatório.

        Returns:
            Tupla (base64_string, hash_value).
        """
        hash_results = report_data.get("hash_results", [])
        case_hash = str(hash_results[0].get("hash_value", "")) if hash_results else ""

        if not case_hash:
            return "", ""

        qr_data = {
            "type": "lexproof_verification",
            "version": report_data.get("schema_version", "1.0"),
            "case_hash": case_hash,
            "generated_at": report_data.get("report_generated_at", ""),
        }
        qr_image = self.qr_generator.generate_verification_qr(qr_data)

        import io
        buffer = io.BytesIO()
        qr_image.save(buffer, format="PNG")
        b64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_string, case_hash

    def _format_file_size(self, size_bytes: int) -> str:
        """Formata tamanho de arquivo em unidades legíveis."""
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
