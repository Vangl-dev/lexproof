from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lexproof.models.message import MessageType, WhatsAppMessage
from lexproof.parsers.base import BaseParser, ParseError

logger = logging.getLogger(__name__)

_SYSTEM_MESSAGES = {
    "messages and calls are end-to-end encrypted",
    "messages and calls are end to end encrypted",
    "as mensagens e as chamadas são criptografadas de ponta a ponta",
    "no one outside of this chat",
    "ninguém fora desta conversa",
    "you created group",
    "você criou o grupo",
    "you added",
    "você adicionou",
    "you were added",
    "você foi adicionado",
    "you left",
    "você saiu",
    "you changed this group",
    "você alterou",
    "security code changed",
    "o código de segurança mudou",
    "this message was deleted",
    "esta mensagem foi apagada",
    "this message was edited",
    "esta mensagem foi editada",
    "you turned on disappearing messages",
    "você ativou as mensagens temporárias",
    "you turned off disappearing messages",
    "você desativou as mensagens temporárias",
    "waiting for this message",
    "aguardando esta mensagem",
    "tap to download",
    "toque para baixar",
    "this chat is with a business account",
    "esta conversa é com uma conta empresarial",
}

_DELETED_PATTERNS = [
    r"<\s*this message was deleted\s*>",
    r"<\s*esta mensagem foi apagada\s*>",
]

_EDITED_PATTERNS = [
    r"<\s*this message was edited\s*>",
    r"<\s*esta mensagem foi editada\s*>",
]

_MEDIA_PATTERNS = [
    r"<\s*media omitted\s*>",
    r"<\s*m[ií]dia ocultada\s*>",
    r"<\s*image omitted\s*>",
    r"<\s*imagem ocultada\s*>",
    r"<\s*video omitted\s*>",
    r"<\s*v[ií]deo ocultado\s*>",
    r"<\s*audio omitted\s*>",
    r"<\s*[aá]udio ocultado\s*>",
    r"<\s*sticker omitted\s*>",
    r"<\s*figurinha ocultada\s*>",
    r"<\s*document omitted\s*>",
    r"<\s*documento ocultado\s*>",
    r"<\s*gif omitted\s*>",
]

_STICKER_PATTERN = r"<\s*figurinha\s*>"
_AUDIO_PATTERN = r"<\s*[aá]udio\s*>"
_VIDEO_PATTERN = r"<\s*v[ií]deo\s*>"

_LINK_PATTERN = re.compile(
    r"https?://[^\s]+", re.IGNORECASE
)

_TIMESTAMP_BR = re.compile(
    r"^(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\s*[,\-]\s*(.+)"
)
_TIMESTAMP_INT = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*[,\-]\s*(.+)",
    re.IGNORECASE,
)

_FORMAT_BR = "br"
_FORMAT_INT = "int"
_FORMAT_UNKNOWN = "unknown"


class WhatsAppParser(BaseParser):
    """Parser para arquivos de conversa exportados do WhatsApp.

    Suporta ambos os formatos de data brasileiro (DD/MM/YYYY HH:MM)
    e internacional (MM/DD/YY, HH:MM AM/PM), com detecção automática.
    """

    def __init__(self) -> None:
        """Inicializa o parser WhatsApp."""
        self._detected_format: Optional[str] = None

    def parse(self, file_path: Path) -> list[WhatsAppMessage]:
        """Extrai mensagens de um arquivo de conversa WhatsApp.

        Args:
            file_path: Caminho para o arquivo .txt exportado do WhatsApp.

        Returns:
            Lista de WhatsAppMessage extraídas do arquivo.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ParseError: Se o parsing falhar completamente.
        """
        content = self._read_file_with_encoding_detection(file_path)
        lines = content.split("\n")

        if not lines:
            logger.warning("Arquivo vazio: %s", file_path.name)
            return []

        self._detected_format = self._detect_format(lines)
        logger.info(
            "Formato detectado para %s: %s",
            file_path.name,
            self._detected_format,
        )

        messages = self._parse_lines(lines)
        logger.info(
            "Extraídas %d mensagens de %s", len(messages), file_path.name
        )
        return messages

    def validate(self, file_path: Path) -> bool:
        """Verifica se o arquivo parece ser uma exportação WhatsApp válida.

        Args:
            file_path: Caminho para o arquivo.

        Returns:
            True se o arquivo existir e pelo menos uma linha tenha formato válido.
        """
        if not file_path.exists():
            return False

        try:
            content = self._read_file_with_encoding_detection(file_path)
        except ParseError:
            return False

        lines = content.split("\n")
        fmt = self._detect_format(lines)
        if fmt == _FORMAT_UNKNOWN:
            return False

        timestamp_pattern = (
            _TIMESTAMP_BR if fmt == _FORMAT_BR else _TIMESTAMP_INT
        )
        match_count = 0
        for line in lines[:50]:
            line = self.clean_text(line)
            if timestamp_pattern.match(line):
                match_count += 1
        return match_count >= 2

    def _detect_format(self, lines: list[str]) -> str:
        """Detecta automaticamente o formato de data do arquivo.

        Analisa as primeiras 20 linhas para determinar se o formato
        é brasileiro ou internacional.

        Args:
            lines: Lista de linhas do arquivo.

        Returns:
            Formato detectado (_FORMAT_BR, _FORMAT_INT ou _FORMAT_UNKNOWN).
        """
        br_count = 0
        int_count = 0
        sample = lines[:20]

        for line in sample:
            line = self.clean_text(line)
            if _TIMESTAMP_BR.match(line):
                br_count += 1
            elif _TIMESTAMP_INT.match(line):
                int_count += 1

        if br_count > int_count:
            return _FORMAT_BR
        if int_count > br_count:
            return _FORMAT_INT
        return _FORMAT_UNKNOWN

    def _parse_lines(self, lines: list[str]) -> list[WhatsAppMessage]:
        """Processa todas as linhas e monta a lista de mensagens.

        Args:
            lines: Lista de linhas do arquivo.

        Returns:
            Lista de mensagens parseadas.
        """
        messages: list[WhatsAppMessage] = []
        current_message: Optional[dict[str, object]] = None

        for line_num, raw_line in enumerate(lines, start=1):
            line = self.clean_text(raw_line)
            if not line:
                continue

            match = self._match_timestamp(line)
            if match:
                if current_message is not None:
                    messages.append(self._build_message(current_message))
                timestamp_str, rest = match
                timestamp = self._parse_timestamp(timestamp_str)
                sender, content = self._split_sender_content(rest)
                current_message = {
                    "line_number": line_num,
                    "timestamp": timestamp,
                    "sender": sender,
                    "content": content,
                    "raw_text": raw_line.rstrip("\n\r"),
                    "continuations": [],
                }
            else:
                if current_message is not None:
                    current_message["continuations"].append(line)  # type: ignore[arg-type]
                else:
                    logger.debug(
                        "Linha %d sem contexto de mensagem: %s", line_num, line[:50]
                    )

        if current_message is not None:
            messages.append(self._build_message(current_message))

        return messages

    def _match_timestamp(self, line: str) -> Optional[tuple[str, str]]:
        """Tenta casar a linha com um padrão de timestamp.

        Args:
            line: Linha limpa.

        Returns:
            Tupla (timestamp_str, rest) ou None.
        """
        if self._detected_format == _FORMAT_BR:
            m = _TIMESTAMP_BR.match(line)
            if m:
                return m.group(1), m.group(2)
        elif self._detected_format == _FORMAT_INT:
            m = _TIMESTAMP_INT.match(line)
            if m:
                return m.group(1), m.group(2)
        else:
            m = _TIMESTAMP_BR.match(line)
            if m:
                return m.group(1), m.group(2)
            m = _TIMESTAMP_INT.match(line)
            if m:
                return m.group(1), m.group(2)
        return None

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Converte a string de timestamp em datetime.

        Args:
            timestamp_str: String de data/hora.

        Returns:
            Objeto datetime parseado.
        """
        timestamp_str = timestamp_str.strip().rstrip(",")
        formats_br = [
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
        ]
        formats_int = [
            "%m/%d/%y, %I:%M %p",
            "%m/%d/%y %I:%M %p",
            "%m/%d/%Y, %I:%M %p",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%y, %H:%M",
            "%m/%d/%y %H:%M",
            "%m/%d/%Y, %H:%M",
            "%m/%d/%Y %H:%M",
        ]

        all_formats: list[str]
        if self._detected_format == _FORMAT_BR:
            all_formats = formats_br + formats_int
        elif self._detected_format == _FORMAT_INT:
            all_formats = formats_int + formats_br
        else:
            all_formats = formats_br + formats_int

        for fmt in all_formats:
            try:
                return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        logger.warning("Não foi possível parsear timestamp: %s", timestamp_str)
        return datetime.min.replace(tzinfo=timezone.utc)

    def _split_sender_content(self, rest: str) -> tuple[str, str]:
        """Separa o remetente do conteúdo da mensagem.

        Args:
            rest: Texto após o timestamp.

        Returns:
            Tupla (remetente, conteúdo).
        """
        colon_pos = rest.find(":")
        if colon_pos == -1:
            return "Desconhecido", rest

        sender = rest[:colon_pos].strip()
        content = rest[colon_pos + 1:].strip()
        return sender, content

    def _build_message(self, msg_data: dict[str, object]) -> WhatsAppMessage:
        """Constrói um WhatsAppMessage a partir dos dados coletados.

        Args:
            msg_data: Dicionário com dados da mensagem.

        Returns:
            Objeto WhatsAppMessage.
        """
        sender = str(msg_data["sender"])
        content = str(msg_data["content"])
        raw_text = str(msg_data["raw_text"])
        continuations = msg_data.get("continuations", [])

        if continuations:
            full_content = content + "\n" + "\n".join(str(c) for c in continuations)
        else:
            full_content = content

        message_type = self._classify_message(full_content)
        is_deleted = self._is_deleted(full_content)
        is_edited = self._is_edited(full_content)
        media_reference = self._extract_media_reference(full_content)
        has_link = bool(_LINK_PATTERN.search(full_content))

        if has_link and message_type == MessageType.TEXT:
            message_type = MessageType.LINK

        if is_deleted:
            message_type = MessageType.DELETED
        elif is_edited:
            message_type = MessageType.EDITED

        return WhatsAppMessage(
            line_number=int(msg_data["line_number"]),
            timestamp=msg_data["timestamp"],  # type: ignore[arg-type]
            sender=sender,
            content=full_content,
            message_type=message_type,
            is_deleted=is_deleted,
            is_edited=is_edited,
            media_reference=media_reference,
            raw_text=raw_text,
        )

    def _classify_message(self, content: str) -> MessageType:
        """Classifica o tipo de mensagem com base no conteúdo.

        Args:
            content: Texto da mensagem.

        Returns:
            Tipo da mensagem detectado.
        """
        lower = content.lower()

        for pattern in _DELETED_PATTERNS:
            if re.search(pattern, lower):
                return MessageType.DELETED

        for pattern in _EDITED_PATTERNS:
            if re.search(pattern, lower):
                return MessageType.EDITED

        for system_msg in _SYSTEM_MESSAGES:
            if system_msg in lower:
                return MessageType.SYSTEM

        for pattern in _MEDIA_PATTERNS:
            if re.search(pattern, lower):
                return MessageType.MEDIA

        if re.search(_STICKER_PATTERN, lower):
            return MessageType.STICKER
        if re.search(_AUDIO_PATTERN, lower):
            return MessageType.AUDIO
        if re.search(_VIDEO_PATTERN, lower):
            return MessageType.VIDEO

        return MessageType.TEXT

    def _is_deleted(self, content: str) -> bool:
        """Verifica se a mensagem foi deletada.

        Args:
            content: Texto da mensagem.

        Returns:
            True se a mensagem foi deletada.
        """
        lower = content.lower()
        return any(re.search(p, lower) for p in _DELETED_PATTERNS)

    def _is_edited(self, content: str) -> bool:
        """Verifica se a mensagem foi editada.

        Args:
            content: Texto da mensagem.

        Returns:
            True se a mensagem foi editada.
        """
        lower = content.lower()
        return any(re.search(p, lower) for p in _EDITED_PATTERNS)

    def _extract_media_reference(self, content: str) -> Optional[str]:
        """Extrai referência de mídia se presente.

        Args:
            content: Texto da mensagem.

        Returns:
            Descrição da mídia ou None.
        """
        lower = content.lower()
        media_map = {
            "figurinha": "sticker",
            "sticker": "sticker",
            "<audio": "audio",
            "<áudio": "audio",
            "áudio": "audio",
            "audio": "audio",
            "video": "video",
            "vídeo": "video",
            "imagem": "image",
            "image": "image",
            "foto": "image",
            "documento": "document",
            "document": "document",
            "gif": "gif",
        }
        for keyword, ref_type in media_map.items():
            if keyword in lower:
                return ref_type
        return None
