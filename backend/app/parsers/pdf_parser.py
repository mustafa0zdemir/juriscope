import fitz  # PyMuPDF

from app.parsers.base import DocumentParser


class PdfParser(DocumentParser):

    def parse(self, content: bytes) -> tuple[str, int, str]:
        extracted_text = ""
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = len(doc)
            for page in doc:
                text = page.get_text()
                if text:
                    extracted_text += text + "\n"
            doc.close()
            return extracted_text.strip(), page_count, "PyMuPDF"
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {str(e)}")
