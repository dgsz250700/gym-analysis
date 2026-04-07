import imaplib
import email.message
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
import re


# ========= CONFIGURA ESTO =========
EMAIL_ADDRESS = "martgarcia1010@gmail.com"
APP_PASSWORD = "yhhc cipo stbl tgho"

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

SAVE_DIR = Path("/home/digest/.openclaw/workspace/inbox_samples")
# ==================================


def safe_decode_header(value: str | None) -> str:
    """Decodifica encabezados MIME de forma segura."""
    if not value:
        return ""

    parts = decode_header(value)
    decoded = []

    for part, encoding in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(encoding or "utf-8", errors="ignore"))
        else:
            decoded.append(part)

    return "".join(decoded).strip()


def clean_filename(text: str, max_len: int = 60) -> str:
    """Limpia texto para usarlo como nombre de archivo."""
    text = text.strip().replace(" ", "_")
    text = re.sub(r"[^\w\-_.]", "", text)
    return text[:max_len] if text else "email"


def extract_plain_text(msg: email.message.Message) -> str:
    """Extrae el cuerpo en texto plano si existe."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if (
                content_type == "text/plain"
                and "attachment" not in content_disposition.lower()
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="ignore").strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(errors="ignore").strip()

    return ""


def main() -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    print("Conectando a Gmail...")
    imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)

    try:
        imap.login(EMAIL_ADDRESS, APP_PASSWORD)
        print("Login exitoso.")

        status, _ = imap.select("INBOX")
        if status != "OK":
            raise RuntimeError("No se pudo abrir INBOX.")

        # Busca correos no leídos
        status, message_ids = imap.search(None, 'UNSEEN SINCE "11-Mar-2026"')
        if status != "OK":
            raise RuntimeError("No se pudo buscar mensajes UNSEEN.")

        ids = message_ids[0].split()

        if not ids:
            print("No hay correos no leídos para procesar.")
            return

        print(f"Se encontraron {len(ids)} correos no leídos.")

        for msg_id in ids:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                print(f"No se pudo descargar el mensaje {msg_id.decode()}. Se omite.")
                continue

            raw_email = None
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    raw_email = response_part[1]
                    break

            if raw_email is None:
                print(f"Mensaje {msg_id.decode()} vacío o inválido. Se omite.")
                continue

            msg = email.message_from_bytes(raw_email)

            subject = safe_decode_header(msg.get("Subject"))
            sender = safe_decode_header(msg.get("From"))
            date_raw = msg.get("Date", "")

            try:
                dt = parsedate_to_datetime(date_raw)
                date_iso = dt.isoformat()
                date_for_name = dt.strftime("%Y-%m-%d_%H-%M")
            except Exception:
                date_iso = date_raw
                date_for_name = "unknown_date"

            body = extract_plain_text(msg)

            safe_subject = clean_filename(subject)
            filename = f"{msg_id.decode()}_{date_for_name}_{safe_subject}.txt"
            filepath = SAVE_DIR / filename

            content = (
                f"Subject: {subject}\n"
                f"From: {sender}\n"
                f"Date: {date_iso}\n"
                f"Message-ID: {msg.get('Message-ID', '')}\n\n"
                f"Body:\n{body}\n"
            )

            filepath.write_text(content, encoding="utf-8")
            print(f"Guardado: {filepath.name}")

            # Marcar como leído para no reprocesarlo
            imap.store(msg_id, "+FLAGS", "\\Seen")
            print(f"Marcado como leído: {msg_id.decode()}")

        print("Proceso completado.")

    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()

if __name__ == "__main__":
    main()