import io

import docx

from app.parsers.base import DocumentParser


class DocxParser(DocumentParser):

    def parse(self, content: bytes) -> tuple[str, int, str]:
        extracted_text = ""
        try:
            doc = docx.Document(io.BytesIO(content))
            # DOCX format doesn't have a strict concept of "pages" like PDF.
            # We'll return 1 or an estimate if needed, but 1 is safe.
            page_count = 1
            for para in doc.paragraphs:
                text = para.text
                if text:
                    extracted_text += text + "\n"
            return extracted_text.strip(), page_count, "python-docx"
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX: {str(e)}")
