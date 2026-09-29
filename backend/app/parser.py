import io
import email
from email import policy
import pypdf

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    ext = filename.lower().split('.')[-1]

    # Handle Plain Text
    if ext == 'txt':
        return file_bytes.decode('utf-8', errors='ignore')

    # Handle Email Files (.eml) with Attachment Inspection
    elif ext == 'eml':
        msg = email.message_from_bytes(file_bytes, policy=policy.default)
        subject = msg.get('subject', 'No Subject')
        sender = msg.get('from', 'Unknown Sender')
        body = msg.get_body(preferencelist=('plain', 'html'))
        body_text = body.get_content() if body else ""

        full_content = f"Subject: {subject}\nFrom: {sender}\n\nBody:\n{body_text}\n"

        # Extract text from embedded attachments
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in content_disposition:
                    att_name = part.get_filename() or "attachment"
                    att_bytes = part.get_payload(decode=True)
                    if att_bytes:
                        att_text = extract_text_from_file(att_bytes, att_name)
                        if att_text.strip():
                            full_content += f"\n--- Attached File ({att_name}) ---\n{att_text}\n"

        return full_content

    # Handle PDF
    elif ext == 'pdf':
        pdf_file = io.BytesIO(file_bytes)
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text

    return ""