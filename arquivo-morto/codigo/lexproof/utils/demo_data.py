"""Demo data generators for LexProof report and UI testing.

Provides realistic Brazilian legal case data, WhatsApp chat exports,
and forensic metadata for development and testing purposes.
"""

from __future__ import annotations


def generate_demo_case() -> dict:
    """Generate a complete demo case with realistic data.

    Returns:
        A dict matching the case_data structure used throughout the
        LexProof application, including metadata, evidence files,
        hashes, custody chain, verifications, and inconsistencies.
    """
    return {
        "metadata": {
            "case_id": "LEX-2024-00042",
            "title": "Investigacao de Ameacas via WhatsApp",
            "description": (
                "Analise de conversas do WhatsApp contendo ameacas e injurias "
                "direcionadas a vítima, com coleta de evidencias digitais e "
                "verificacao de integridade dos dados."
            ),
            "examiner": "Dr. Maria Silva",
            "organization": "Instituto de Criminalistica Digital",
            "created_at": "2024-03-15T14:30:00",
        },
        "evidence_files": [
            {
                "name": "WhatsApp_Chat_Joao.txt",
                "path": "/demo/WhatsApp_Chat_Joao.txt",
                "type": "txt",
                "size": 15420,
                "imported_at": "2024-03-15T14:32:00",
                "thumbnail_path": None,
            },
            {
                "name": "print_conversa_01.png",
                "path": "/demo/print_conversa_01.png",
                "type": "png",
                "size": 245760,
                "imported_at": "2024-03-15T14:33:00",
                "thumbnail_path": None,
            },
            {
                "name": "print_conversa_02.png",
                "path": "/demo/print_conversa_02.png",
                "type": "png",
                "size": 312000,
                "imported_at": "2024-03-15T14:33:30",
                "thumbnail_path": None,
            },
        ],
        "hashes": [
            {
                "file_name": "WhatsApp_Chat_Joao.txt",
                "sha256": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678",
                "sha3_512": (
                    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                ),
                "blake3": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
            },
            {
                "file_name": "print_conversa_01.png",
                "sha256": "b2c3d4e5f6a1789012345678901234567890bcdef1234567890bcdef12345678",
                "sha3_512": (
                    "123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                    "123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                ),
                "blake3": "bcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789a",
            },
            {
                "file_name": "print_conversa_02.png",
                "sha256": "c3d4e5f6a1b2789012345678901234567890cdef1234567890cdef12345678",
                "sha3_512": (
                    "23456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                    "23456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                ),
                "blake3": "cdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789ab",
            },
        ],
        "global_hash": (
            "fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321"
        ),
        "custody_chain": [
            {
                "timestamp": "2024-03-15T14:30:00",
                "user": "Dr. Maria Silva",
                "action": "Caso criado",
                "details": "Sessao de analise iniciada",
            },
            {
                "timestamp": "2024-03-15T14:32:15",
                "user": "Dr. Maria Silva",
                "action": "Arquivo importado",
                "details": "WhatsApp_Chat_Joao.txt adicionado como evidencia",
            },
            {
                "timestamp": "2024-03-15T14:33:10",
                "user": "Dr. Maria Silva",
                "action": "Arquivo importado",
                "details": "print_conversa_01.png adicionado como evidencia",
            },
            {
                "timestamp": "2024-03-15T14:33:45",
                "user": "Dr. Maria Silva",
                "action": "Arquivo importado",
                "details": "print_conversa_02.png adicionado como evidencia",
            },
            {
                "timestamp": "2024-03-15T14:35:00",
                "user": "Dr. Maria Silva",
                "action": "Hashes calculados",
                "details": "SHA256, SHA3-512 e BLAKE3 gerados para todos os arquivos",
            },
            {
                "timestamp": "2024-03-15T14:40:00",
                "user": "Dr. Maria Silva",
                "action": "OCR executado",
                "details": "Imagens processadas via OCR Tesseract (por=eng+ita)",
            },
            {
                "timestamp": "2024-03-15T14:45:00",
                "user": "Dr. Maria Silva",
                "action": "Verificacao concluida",
                "details": "Integridade verificada, 2 inconsistencias encontradas",
            },
        ],
        "verifications": [
            {
                "check_name": "Integridade dos Arquivos",
                "status": "PASS",
                "details": "Todos os arquivos estao intactos",
            },
            {
                "check_name": "OCR vs TXT",
                "status": "PASS",
                "details": "32 mensagens verificadas com sucesso",
            },
            {
                "check_name": "Ordem Cronologica",
                "status": "WARNING",
                "details": "2 mensagens com timestamps fora de ordem",
            },
            {
                "check_name": "Metadados EXIF",
                "status": "INFO",
                "details": "2 imagens sem dados EXIF (normal para screenshots)",
            },
        ],
        "inconsistencies": [
            "Mensagem #15: timestamp anterior a mensagem #14",
            "Mensagem #28: conteudo editado detectado",
        ],
    }


def generate_demo_whatsapp_txt() -> str:
    """Generate a sample WhatsApp exported text file content.

    Returns:
        A string containing a realistic Brazilian WhatsApp chat export
        with approximately 30 messages, including text, media placeholders,
        deleted messages, links, and timestamps.

    The format follows the standard WhatsApp chat export layout::

        15/03/2024 14:30 - Joao: Oi, tudo bem?
    """
    lines: list[str] = [
        "15/03/2024 14:30 - Joao: Oi, tudo bem?",
        "15/03/2024 14:31 - Maria: Oi! Tudo sim, e voce?",
        "15/03/2024 14:32 - Joao: Preciso falar com voce sobre uma coisa",
        "15/03/2024 14:33 - Maria: Pode falar, estou ouvindo",
        "15/03/2024 14:35 - Joao: Daqui a pouco passo aí em casa",
        "15/03/2024 14:36 - Maria: Ok, pode vir sim",
        "15/03/2024 14:40 - Joao: <Midia ocultada>",
        "15/03/2024 14:41 - Maria: Que foto bonita!",
        "15/03/2024 14:45 - Joao: Essa foi no domingo",
        "15/03/2024 14:46 - Maria: Adorei",
        "15/03/2024 14:50 - Joao: Voce viu a noticia de hoje?",
        "15/03/2024 14:51 - Maria: Nao, qual?",
        "15/03/2024 14:52 - Joao: Aquela do site https://exemplo.com/noticia/123",
        "15/03/2024 14:53 - Maria: Nossa, que absurdo!",
        "15/03/2024 14:54 - Joao: Pois e, ta complicado",
        "15/03/2024 14:55 - Joao: Vou te mandar um arquivo",
        "15/03/2024 14:56 - Joao: <Arquivo anexado: documento.pdf>",
        "15/03/2024 14:57 - Maria: Recebi, obrigada",
        "15/03/2024 15:00 - Joao: Qualquer coisa me avisa",
        "15/03/2024 15:01 - Maria: Certo",
        "15/03/2024 15:10 - Joao: Amanha tem reuniao la as 9h",
        "15/03/2024 15:11 - Maria: Ta, vou estar la",
        "15/03/2024 15:12 - Joao: Nao esquece os papeis",
        "15/03/2024 15:13 - Maria: Ja to com eles aqui",
        "15/03/2024 15:15 - Joao: <Mensagem apagada>",
        "15/03/2024 15:20 - Maria: Ja ta tudo certo entao",
        "15/03/2024 15:21 - Joao: Bom, ate la",
        "15/03/2024 15:22 - Maria: Ate mais!",
        "15/03/2024 15:30 - Joao: E aquele outro assunto?",
        "15/03/2024 15:31 - Maria: Ah sim, deixa pra depois",
        "15/03/2024 15:32 - Joao: Tudo bem, combinado",
    ]
    return "\n".join(lines) + "\n"
