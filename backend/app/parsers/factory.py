from app.parsers.base import DocumentParser
from app.parsers.docx_parser import DocxParser
from app.parsers.pdf_parser import PdfParser


def get_parser(file_extension: str) -> DocumentParser:
    """
    Returns the appropriate parser for the given file extension.
    Raises ValueError if the extension is not supported.
    """
    ext = file_extension.lower()
    if ext == ".pdf":
        return PdfParser()
    elif ext in [".doc", ".docx"]:
        return DocxParser()
    else:
        raise ValueError(f"No parser found for extension: {file_extension}")
