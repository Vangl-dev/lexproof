from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from lexproof.models.message import WhatsAppMessage
from lexproof.models.ocr_result import OCRResult

logger = logging.getLogger(__name__)

TIMESTAMP_PATTERNS = [
    r"\d{1,2}/\d{1,2}/\d{2,4}[\s,]+\d{1,2}:\d{2}",
    r"\d{4}-\d{2}-\d{2}[\s,]+\d{1,2}:\d{2}",
    r"\d{1,2}:\d{2}\s*[APap][Mm]",
    r"\d{1,2}:\d{2}:\d{2}",
]

SENDER_PATTERN = r"^[^\n:]{1,30}(?=[:\u200b]|$)"


class OCRProcessor:
    """Orquestrador que gerencia múltiplas engines OCR.

    Coordena a extração de texto, detecção de campos específicos
    de conversas WhatsApp, e comparação com arquivos .txt.
    """

    def __init__(self) -> None:
        """Inicializa o processador OCR."""
        self._engines: dict[str, Any] = {}

    def _get_engine(self, engine_name: str) -> Any:
        """Obtém ou cria uma instância da engine OCR.

        Args:
            engine_name: Nome da engine ('tesseract' ou 'easyocr').

        Returns:
            Instância da engine OCR.

        Raises:
            ValueError: Se a engine não for reconhecida.
        """
        if engine_name not in self._engines:
            if engine_name == "tesseract":
                from lexproof.ocr.tesseract_engine import TesseractOCR

                self._engines[engine_name] = TesseractOCR()
            elif engine_name == "easyocr":
                from lexproof.ocr.easyocr_engine import EasyOCREngine

                self._engines[engine_name] = EasyOCREngine()
            else:
                raise ValueError(
                    f"Engine OCR desconhecida: '{engine_name}'. "
                    "Engines disponíveis: 'tesseract', 'easyocr'"
                )
        return self._engines[engine_name]

    def process_image(
        self, image_path: Path, engine: str = "tesseract"
    ) -> OCRResult:
        """Processa uma imagem usando a engine OCR especificada.

        Extrai texto completo e detecta timestamps, remetentes e
        mensagens da imagem.

        Args:
            image_path: Caminho para a imagem de evidência.
            engine: Nome da engine OCR ('tesseract' ou 'easyocr').

        Returns:
            Objeto OCRResult com todos os dados extraídos.

        Raises:
            FileNotFoundError: Se a imagem não existir.
            ValueError: Se a engine não for reconhecida.
            RuntimeError: Se ocorrer erro durante o processamento.
        """
        logger.info("Processando imagem %s com engine '%s'", image_path, engine)
        start = time.monotonic()

        ocr_engine = self._get_engine(engine)

        try:
            text = ocr_engine.extract_text(image_path)
        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Erro ao processar {image_path} com {engine}: {e}"
            ) from e

        timestamps = self.extract_timestamps(text)
        senders = self.extract_senders(text)
        messages = self.extract_messages(text)

        elapsed = time.monotonic() - start

        result = OCRResult(
            source_image=str(image_path),
            extracted_text=text,
            confidence=0.0,
            detected_timestamps=timestamps,
            detected_senders=senders,
            detected_messages=messages,
            engine_used=engine,
            processing_time=elapsed,
        )

        logger.info(
            "OCR concluído: %d timestamps, %d senders, %d mensagens em %.2fs",
            len(timestamps),
            len(senders),
            len(messages),
            elapsed,
        )
        return result

    def process_image_with_boxes(
        self, image_path: Path, engine: str = "tesseract"
    ) -> dict[str, Any]:
        """Processa imagem retornando texto com bounding boxes.

        Args:
            image_path: Caminho para a imagem.
            engine: Nome da engine OCR.

        Returns:
            Dicionário com 'result' (OCRResult) e 'boxes'
            (lista de boxes com texto e posição).
        """
        ocr_engine = self._get_engine(engine)

        boxes = ocr_engine.extract_text_with_boxes(image_path)
        text = " ".join(b[0] for b in boxes)

        timestamps = self.extract_timestamps(text)
        senders = self.extract_senders(text)
        messages = self.extract_messages(text)

        avg_conf = sum(b[2] for b in boxes) / len(boxes) if boxes else 0.0

        result = OCRResult(
            source_image=str(image_path),
            extracted_text=text,
            confidence=avg_conf,
            detected_timestamps=timestamps,
            detected_senders=senders,
            detected_messages=messages,
            engine_used=engine,
            processing_time=0.0,
        )

        return {"result": result, "boxes": boxes}

    @staticmethod
    def extract_timestamps(text: str) -> list[str]:
        """Detecta timestamps no texto extraído pelo OCR.

        Procura por padrões comuns de data/hora em conversas WhatsApp
        em formato brasileiro e internacional.

        Args:
            text: Texto extraído pelo OCR.

        Returns:
            Lista de timestamps encontrados (strings originais).
        """
        found: list[str] = []
        seen: set[str] = set()

        for pattern in TIMESTAMP_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                normalized = match.strip()
                if normalized not in seen:
                    seen.add(normalized)
                    found.append(normalized)

        logger.debug("Timestamps detectados: %d", len(found))
        return found

    @staticmethod
    def extract_senders(text: str) -> list[str]:
        """Detecta nomes/números de remetentes no texto OCR.

        Analisa o padrão 'Remetente: mensagem' comum em prints
        de conversas WhatsApp.

        Args:
            text: Texto extraído pelo OCR.

        Returns:
            Lista de remetentes encontrados (strings únicas).
        """
        senders: list[str] = []
        seen: set[str] = set()

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            match = re.match(SENDER_PATTERN, line)
            if match:
                name = match.group(0).strip()
                if name and name not in seen and len(name) > 1:
                    seen.add(name)
                    senders.append(name)

        logger.debug("Remetentes detectados: %d", len(senders))
        return senders

    @staticmethod
    def extract_messages(text: str) -> list[str]:
        """Segmenta mensagens individuais do texto OCR.

        Tenta identificar blocos de mensagens separados por timestamps
        ou padrões de remetente.

        Args:
            text: Texto extraído pelo OCR.

        Returns:
            Lista de mensagens segmentadas.
        """
        messages: list[str] = []
        current_parts: list[str] = []

        full_pattern = re.compile(
            r"(?:\d{1,2}/\d{1,2}/\d{2,4}[\s,]+\d{1,2}:\d{2}"
            r"|\d{4}-\d{2}-\d{2}[\s,]+\d{1,2}:\d{2}"
            r"|\d{1,2}:\d{2}\s*[APap][Mm])"
        )

        for line in text.split("\n"):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            if full_pattern.search(line_stripped):
                if current_parts:
                    msg = "\n".join(current_parts).strip()
                    if msg:
                        messages.append(msg)
                current_parts = [line_stripped]
            else:
                current_parts.append(line_stripped)

        if current_parts:
            msg = "\n".join(current_parts).strip()
            if msg:
                messages.append(msg)

        if len(messages) <= 1 and text.strip():
            messages = [line.strip() for line in text.split("\n") if line.strip()]

        logger.debug("Mensagens segmentadas: %d", len(messages))
        return messages

    @staticmethod
    def compare_with_txt(
        ocr_text: str, txt_messages: list[WhatsAppMessage]
    ) -> dict[str, Any]:
        """Compara texto OCR com mensagens extraídas de arquivo .txt.

        Realiza comparação textual entre o que foi extraído por OCR
        e as mensagens já parseadas, identificando correspondências,
        divergências e mensagens ausentes em uma das fontes.

        Args:
            ocr_text: Texto completo extraído pelo OCR.
            txt_messages: Lista de mensagens parseadas do arquivo .txt.

        Returns:
            Dicionário com:
                - matches: mensagens encontradas em ambas as fontes
                - mismatches: mensagens com conteúdo diferente
                - missing_in_ocr: mensagens do .txt não encontradas no OCR
                - missing_in_txt: textos do OCR não encontrados no .txt
                - stats: estatísticas gerais da comparação
        """
        ocr_lower = ocr_text.lower()

        matches: list[dict[str, Any]] = []
        mismatches: list[dict[str, Any]] = []
        missing_in_ocr: list[dict[str, Any]] = []

        for msg in txt_messages:
            content = msg.content.strip()
            if not content or len(content) < 10:
                continue

            content_lower = content.lower()

            if content_lower in ocr_lower:
                matches.append({
                    "timestamp": msg.timestamp.isoformat(),
                    "sender": msg.sender,
                    "content": content,
                })
            else:
                words = set(content_lower.split())
                ocr_words = set(ocr_lower.split())
                overlap = len(words & ocr_words) / max(len(words), 1)

                if overlap > 0.6:
                    mismatches.append({
                        "timestamp": msg.timestamp.isoformat(),
                        "sender": msg.sender,
                        "txt_content": content,
                        "overlap_ratio": round(overlap, 2),
                    })
                else:
                    missing_in_ocr.append({
                        "timestamp": msg.timestamp.isoformat(),
                        "sender": msg.sender,
                        "content": content,
                    })

        missing_in_txt: list[str] = []
        txt_all = " ".join(m.content.lower() for m in txt_messages if m.content)

        ocr_sentences = [s.strip() for s in ocr_text.split("\n") if s.strip()]
        for sentence in ocr_sentences:
            sentence_lower = sentence.lower()
            if len(sentence_lower) < 10:
                continue
            if sentence_lower not in txt_all:
                words = set(sentence_lower.split())
                txt_words = set(txt_all.split())
                overlap = len(words & txt_words) / max(len(words), 1)
                if overlap < 0.4:
                    missing_in_txt.append(sentence)

        stats = {
            "total_ocr_lines": len([l for l in ocr_text.split("\n") if l.strip()]),
            "total_txt_messages": len(txt_messages),
            "matches": len(matches),
            "mismatches": len(mismatches),
            "missing_in_ocr": len(missing_in_ocr),
            "missing_in_txt": len(missing_in_txt),
            "match_rate": round(
                len(matches) / max(len(txt_messages), 1) * 100, 1
            ),
        }

        logger.info(
            "Comparação OCR vs TXT: %d matches, %d mismatches, "
            "%d ausentes no OCR, %d ausentes no TXT",
            len(matches),
            len(mismatches),
            len(missing_in_ocr),
            len(missing_in_txt),
        )

        return {
            "matches": matches,
            "mismatches": mismatches,
            "missing_in_ocr": missing_in_ocr,
            "missing_in_txt": missing_in_txt,
            "stats": stats,
        }
