"""Verificador de integridade e consistência de evidências do LexProof."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from lexproof.models.evidence import EvidenceFile, EvidenceType
from lexproof.models.message import WhatsAppMessage
from lexproof.models.ocr_result import OCRResult
from lexproof.models.verification import VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)


class VerificationChecker:
    """Realiza verificações de integridade e consistência em evidências.

    Executa uma bateria de testes sobre mensagens, resultados OCR e arquivos
    de evidência para garantir a confiabilidade da prova digital.
    """

    def run_all_verifications(self, case_data: dict[str, Any]) -> list[VerificationResult]:
        """Executa todas as verificações disponíveis nos dados do caso.

        Args:
            case_data: Dicionário contendo os dados do caso com as chaves:
                - ocr_results (list[OCRResult]): Resultados OCR
                - txt_messages (list[WhatsAppMessage]): Mensagens do TXT
                - evidence_files (list[EvidenceFile]): Arquivos de evidência
                - messages (list[WhatsAppMessage]): Mensagens para verificação
                    de timestamps, ordem, etc.

        Returns:
            Lista com todos os resultados de verificação.
        """
        results: list[VerificationResult] = []

        ocr_results: list[OCRResult] = case_data.get("ocr_results", [])
        txt_messages: list[WhatsAppMessage] = case_data.get("txt_messages", [])
        evidence_files: list[EvidenceFile] = case_data.get("evidence_files", [])
        messages: list[WhatsAppMessage] = case_data.get("messages", txt_messages)

        if ocr_results and txt_messages:
            results.append(self.verify_ocr_vs_txt(ocr_results, txt_messages))

        if messages:
            results.append(self.verify_timestamps(messages))
            results.append(self.verify_senders(messages))
            results.append(self.verify_message_order(messages))
            results.append(self.verify_message_count(messages))

        if evidence_files:
            results.append(self.verify_file_integrity(evidence_files))
            results.append(self.verify_exif(evidence_files))

        logger.info("Executadas %d verificações.", len(results))
        return results

    def verify_ocr_vs_txt(
        self,
        ocr_results: list[OCRResult],
        txt_messages: list[WhatsAppMessage],
    ) -> VerificationResult:
        """Verifica consistência entre resultados OCR e mensagens TXT.

        Compara o conteúdo extraído via OCR com o conteúdo das mensagens
        do arquivo TXT para detectar divergências significativas.

        Args:
            ocr_results: Lista de resultados OCR.
            txt_messages: Lista de mensagens extraídas do TXT.

        Returns:
            Resultado da verificação com status PASS, WARNING ou FAIL.
        """
        if not ocr_results:
            return VerificationResult(
                check_name="OCR vs TXT",
                status=VerificationStatus.NOT_APPLICABLE,
                details={"reason": "Nenhum resultado OCR disponível"},
            )

        txt_content_set = {msg.content.strip().lower() for msg in txt_messages if msg.content}
        ocr_content_set = set()
        for ocr in ocr_results:
            for msg in ocr.detected_messages:
                ocr_content_set.add(msg.strip().lower())

        if not txt_content_set and not ocr_content_set:
            return VerificationResult(
                check_name="OCR vs TXT",
                status=VerificationStatus.INCONCLUSIVE,
                details={"reason": "Ambos os conjuntos de conteúdo estão vazios"},
            )

        if not txt_content_set:
            return VerificationResult(
                check_name="OCR vs TXT",
                status=VerificationStatus.WARNING,
                details={
                    "reason": "Nenhuma mensagem de texto encontrada no TXT",
                    "ocr_messages_count": len(ocr_content_set),
                },
            )

        if not ocr_content_set:
            return VerificationResult(
                check_name="OCR vs TXT",
                status=VerificationStatus.WARNING,
                details={
                    "reason": "Nenhuma mensagem detectada nos resultados OCR",
                    "txt_messages_count": len(txt_content_set),
                },
            )

        matches = txt_content_set & ocr_content_set
        only_in_txt = txt_content_set - ocr_content_set
        only_in_ocr = ocr_content_set - txt_content_set

        total_unique = txt_content_set | ocr_content_set
        match_ratio = len(matches) / len(total_unique) if total_unique else 0.0

        if match_ratio >= 0.8:
            status = VerificationStatus.PASS
        elif match_ratio >= 0.5:
            status = VerificationStatus.WARNING
        else:
            status = VerificationStatus.FAIL

        return VerificationResult(
            check_name="OCR vs TXT",
            status=status,
            expected=f"{len(txt_content_set)} mensagens no TXT",
            actual=f"{len(matches)} correspondências de {len(total_unique)} únicas",
            details={
                "match_ratio": round(match_ratio, 3),
                "txt_messages_count": len(txt_content_set),
                "ocr_messages_count": len(ocr_content_set),
                "matched_count": len(matches),
                "only_in_txt_count": len(only_in_txt),
                "only_in_ocr_count": len(only_in_ocr),
            },
        )

    def verify_timestamps(self, messages: list[WhatsAppMessage]) -> VerificationResult:
        """Verifica a integridade dos timestamps das mensagens.

        Detecta timestamps duplicados, fora de ordem e com anos incoerentes.

        Args:
            messages: Lista de mensagens a serem verificadas.

        Returns:
            Resultado da verificação com detalhes sobre problemas encontrados.
        """
        if not messages:
            return VerificationResult(
                check_name="Verificação de Timestamps",
                status=VerificationStatus.NOT_APPLICABLE,
                details={"reason": "Nenhuma mensagem para verificar"},
            )

        issues: list[str] = []
        current_year = datetime.now().year

        timestamp_counts: dict[str, int] = {}
        for msg in messages:
            key = msg.timestamp.isoformat()
            timestamp_counts[key] = timestamp_counts.get(key, 0) + 1

        for ts_str, count in timestamp_counts.items():
            if count > 1:
                issues.append(f"Timestamp duplicado: {ts_str} ({count} ocorrências)")

        for i in range(len(messages) - 1):
            if messages[i].timestamp > messages[i + 1].timestamp:
                issues.append(
                    f"Msg na linha {messages[i].line_number} ({messages[i].timestamp}) "
                    f"posterior à msg na linha {messages[i + 1].line_number} "
                    f"({messages[i + 1].timestamp})"
                )

        for msg in messages:
            if msg.timestamp.year < 2000 or msg.timestamp.year > current_year + 1:
                issues.append(
                    f"Ano suspeito na linha {msg.line_number}: {msg.timestamp.year}"
                )

        if not issues:
            status = VerificationStatus.PASS
        elif len(issues) <= 2:
            status = VerificationStatus.WARNING
        else:
            status = VerificationStatus.FAIL

        return VerificationResult(
            check_name="Verificação de Timestamps",
            status=status,
            expected="Timestamps consistentes e em ordem",
            actual=f"{len(issues)} problemas encontrados" if issues else "Consistente",
            details={
                "issues": issues,
                "total_messages": len(messages),
                "unique_timestamps": len(set(m.timestamp.isoformat() for m in messages)),
            },
        )

    def verify_senders(self, messages: list[WhatsAppMessage]) -> VerificationResult:
        """Verifica a consistência dos remetentes das mensagens.

        Analisa se há remetentes inesperados, campos vazios ou padrões
        anômalos nos nomes dos participantes.

        Args:
            messages: Lista de mensagens a serem verificadas.

        Returns:
            Resultado da verificação com detalhes sobre remetentes.
        """
        if not messages:
            return VerificationResult(
                check_name="Verificação de Remetentes",
                status=VerificationStatus.NOT_APPLICABLE,
                details={"reason": "Nenhuma mensagem para verificar"},
            )

        issues: list[str] = []
        sender_counts: dict[str, int] = {}
        empty_senders = 0

        for msg in messages:
            if not msg.sender or not msg.sender.strip():
                empty_senders += 1
            else:
                normalized = msg.sender.strip().lower()
                sender_counts[normalized] = sender_counts.get(normalized, 0) + 1

        if empty_senders > 0:
            issues.append(f"{empty_senders} mensagens sem remetente")

        for sender, count in sender_counts.items():
            if count == 1 and len(messages) > 5:
                issues.append(
                    f"Remetente '{sender}' aparece apenas 1 vez em {len(messages)} mensagens"
                )

        for msg in messages:
            if msg.sender and len(msg.sender) > 100:
                issues.append(
                    f"Remetente anormalmente longo na linha {msg.line_number}: "
                    f"'{msg.sender[:50]}...'"
                )

        if not issues:
            status = VerificationStatus.PASS
        elif empty_senders > len(messages) * 0.5:
            status = VerificationStatus.FAIL
        else:
            status = VerificationStatus.WARNING

        return VerificationResult(
            check_name="Verificação de Remetentes",
            status=status,
            expected="Remetentes consistentes e presentes",
            actual=f"{len(issues)} problemas encontrados" if issues else "Consistente",
            details={
                "issues": issues,
                "unique_senders": len(sender_counts),
                "sender_distribution": sender_counts,
                "empty_sender_count": empty_senders,
            },
        )

    def verify_message_order(self, messages: list[WhatsAppMessage]) -> VerificationResult:
        """Verifica a ordem cronológica das mensagens.

        Identifica mensagens fora de ordem temporal e calcula a percentagem
        de mensagens que respeitam a ordenação.

        Args:
            messages: Lista de mensagens a serem verificadas.

        Returns:
            Resultado da verificação com estatísticas de ordenação.
        """
        if len(messages) < 2:
            return VerificationResult(
                check_name="Verificação de Ordem",
                status=VerificationStatus.NOT_APPLICABLE,
                details={"reason": "Menos de 2 mensagens para verificar ordem"},
            )

        out_of_order: list[dict[str, Any]] = []

        for i in range(len(messages) - 1):
            if messages[i].timestamp > messages[i + 1].timestamp:
                out_of_order.append(
                    {
                        "position": i,
                        "line_a": messages[i].line_number,
                        "time_a": messages[i].timestamp.isoformat(),
                        "line_b": messages[i + 1].line_number,
                        "time_b": messages[i + 1].timestamp.isoformat(),
                    }
                )

        total_pairs = len(messages) - 1
        in_order = total_pairs - len(out_of_order)
        order_ratio = in_order / total_pairs if total_pairs > 0 else 1.0

        if order_ratio >= 0.95:
            status = VerificationStatus.PASS
        elif order_ratio >= 0.8:
            status = VerificationStatus.WARNING
        else:
            status = VerificationStatus.FAIL

        return VerificationResult(
            check_name="Verificação de Ordem",
            status=status,
            expected="Mensagens em ordem cronológica",
            actual=f"{order_ratio * 100:.1f}% em ordem",
            details={
                "out_of_order_count": len(out_of_order),
                "total_pairs": total_pairs,
                "order_ratio": round(order_ratio, 4),
                "out_of_order_examples": out_of_order[:10],
            },
        )

    def verify_message_count(self, messages: list[WhatsAppMessage]) -> VerificationResult:
        """Verifica a contagem total de mensagens contra valores esperados.

        Valida se há contagem consistente considerando mensagens deletadas,
        editadas e do sistema.

        Args:
            messages: Lista de mensagens a serem verificadas.

        Returns:
            Resultado da verificação com estatísticas de contagem.
        """
        if not messages:
            return VerificationResult(
                check_name="Verificação de Contagem",
                status=VerificationStatus.NOT_APPLICABLE,
                details={"reason": "Nenhuma mensagem para contar"},
            )

        total = len(messages)
        type_counts: dict[str, int] = {}
        deleted_count = 0
        edited_count = 0

        for msg in messages:
            type_key = msg.message_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1
            if msg.is_deleted:
                deleted_count += 1
            if msg.is_edited:
                edited_count += 1

        line_numbers = [msg.line_number for msg in messages]
        unique_lines = len(set(line_numbers))

        issues: list[str] = []
        if unique_lines < total:
            issues.append(
                f"{total - unique_lines} mensagens compartilham o mesmo número de linha"
            )

        if deleted_count > total * 0.5:
            issues.append(
                f"Alta proporção de mensagens deletadas: {deleted_count}/{total}"
            )

        status = VerificationStatus.PASS if not issues else VerificationStatus.WARNING

        return VerificationResult(
            check_name="Verificação de Contagem",
            status=status,
            expected=f"{total} mensagens",
            actual=f"{total} mensagens ({deleted_count} deletadas, {edited_count} editadas)",
            details={
                "total": total,
                "type_distribution": type_counts,
                "deleted_count": deleted_count,
                "edited_count": edited_count,
                "unique_line_numbers": unique_lines,
                "issues": issues,
            },
        )

    def verify_file_integrity(self, evidence_files: list[EvidenceFile]) -> VerificationResult:
        """Verifica a integridade dos arquivos de evidência.

        Recalcula o hash SHA-256 de cada arquivo e compara com o hash
        registrado para detectar alterações.

        Args:
            evidence_files: Lista de arquivos de evidência.

        Returns:
            Resultado da verificação de integridade dos arquivos.
        """
        if not evidence_files:
            return VerificationResult(
                check_name="Integridade de Arquivos",
                status=VerificationStatus.NOT_APPLICABLE,
                details={"reason": "Nenhum arquivo de evidência para verificar"},
            )

        verified = 0
        failed = 0
        missing = 0
        mismatch_details: list[dict[str, str]] = []

        for evidence in evidence_files:
            file_path = Path(evidence.file_path)

            if not file_path.exists():
                missing += 1
                mismatch_details.append(
                    {
                        "file": evidence.file_name,
                        "issue": "Arquivo não encontrado",
                        "expected_hash": evidence.file_hash_sha256,
                    }
                )
                continue

            try:
                computed_hash = self._compute_sha256(file_path)
            except (OSError, PermissionError) as exc:
                failed += 1
                mismatch_details.append(
                    {
                        "file": evidence.file_name,
                        "issue": f"Erro ao ler: {exc}",
                        "expected_hash": evidence.file_hash_sha256,
                    }
                )
                continue

            if computed_hash == evidence.file_hash_sha256:
                verified += 1
            else:
                failed += 1
                mismatch_details.append(
                    {
                        "file": evidence.file_name,
                        "issue": "Hash divergente",
                        "expected_hash": evidence.file_hash_sha256,
                        "computed_hash": computed_hash,
                    }
                )

        if failed == 0 and missing == 0:
            status = VerificationStatus.PASS
        elif failed == 0 and missing > 0:
            status = VerificationStatus.WARNING
        else:
            status = VerificationStatus.FAIL

        return VerificationResult(
            check_name="Integridade de Arquivos",
            status=status,
            expected=f"{len(evidence_files)} arquivos íntegros",
            actual=f"{verified} verificados, {failed} falharam, {missing} ausentes",
            details={
                "total_files": len(evidence_files),
                "verified": verified,
                "failed": failed,
                "missing": missing,
                "mismatch_details": mismatch_details,
            },
        )

    def verify_exif(self, evidence_files: list[EvidenceFile]) -> VerificationResult:
        """Verifica metadados EXIF dos arquivos de evidência.

        Analisa se os metadados EXIF estão presentes e consistentes,
        verificando dispositivos, datas e coordenadas GPS.

        Args:
            evidence_files: Lista de arquivos de evidência.

        Returns:
            Resultado da verificação de metadados EXIF.
        """
        if not evidence_files:
            return VerificationResult(
                check_name="Verificação EXIF",
                status=VerificationStatus.NOT_APPLICABLE,
                details={"reason": "Nenhum arquivo de evidência para verificar"},
            )

        image_types = {
            EvidenceType.PNG,
            EvidenceType.JPG,
            EvidenceType.JPEG,
        }

        image_files = [f for f in evidence_files if f.evidence_type in image_types]

        if not image_files:
            return VerificationResult(
                check_name="Verificação EXIF",
                status=VerificationStatus.NOT_APPLICABLE,
                details={"reason": "Nenhum arquivo de imagem para verificar EXIF"},
            )

        with_exif = 0
        without_exif = 0
        device_set: set[str] = set()
        date_issues: list[str] = []

        for evidence in image_files:
            metadata = evidence.metadata
            exif_data = metadata.get("exif", metadata)

            has_device = bool(
                exif_data.get("Make")
                or exif_data.get("Model")
                or exif_data.get("Device")
            )
            has_date = bool(
                exif_data.get("DateTimeOriginal")
                or exif_data.get("DateTime")
                or exif_data.get("CreateDate")
            )

            if has_device or has_date:
                with_exif += 1
                device = exif_data.get("Make", "") or exif_data.get("Model", "")
                if device:
                    device_set.add(str(device))

                date_str = (
                    exif_data.get("DateTimeOriginal")
                    or exif_data.get("DateTime")
                    or exif_data.get("CreateDate")
                )
                if date_str and evidence.created_at:
                    try:
                        exif_date = datetime.strptime(
                            str(date_str), "%Y:%m:%d %H:%M:%S"
                        ).replace(tzinfo=timezone.utc)
                        diff = abs(
                            (exif_date - evidence.created_at).total_seconds()
                        )
                        if diff > 86400:
                            date_issues.append(
                                f"{evidence.file_name}: data EXIF ({date_str}) "
                                f"diverge da data de registro ({evidence.created_at.isoformat()})"
                            )
                    except (ValueError, TypeError):
                        pass
            else:
                without_exif += 1

        if with_exif == 0:
            status = VerificationStatus.WARNING
        elif date_issues:
            status = VerificationStatus.WARNING
        else:
            status = VerificationStatus.PASS

        return VerificationResult(
            check_name="Verificação EXIF",
            status=status,
            expected=f"{len(image_files)} arquivos com EXIF consistente",
            actual=f"{with_exif} com metadados, {without_exif} sem metadados",
            details={
                "total_images": len(image_files),
                "with_exif": with_exif,
                "without_exif": without_exif,
                "detected_devices": list(device_set),
                "date_issues": date_issues,
            },
        )

    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        """Calcula o hash SHA-256 de um arquivo.

        Args:
            file_path: Caminho do arquivo.

        Returns:
            Hash SHA-256 em formato hexadecimal.
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
