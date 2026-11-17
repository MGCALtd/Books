"""PDF extraction with bounded diagnostics and complete page provenance."""
import logging
import sys
from pypdf import PdfReader

from .core import Page, NeedsOCR


class PDFDiagnostics(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.count = 0
        self.samples = []

    def emit(self, record):
        self.count += 1
        if len(self.samples) < 3:
            self.samples.append(record.getMessage()[:250])


def extract_pdf(path):
    capture = PDFDiagnostics()
    logger = logging.getLogger('pypdf')
    previous_propagation = logger.propagate
    previous_level = logger.level
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    logger.addHandler(capture)
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(''):
            raise ValueError('Encrypted PDF requires an unlocked copy; no password guessing performed.')
        metadata = reader.metadata
        title = str(metadata.title or path.stem) if metadata else path.stem
        author = str(metadata.author or '') if metadata else ''
        labels = reader.page_labels
        pages, warnings = [], []
        total = len(reader.pages)
        for number, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or '').strip()
            if len(text) < 30:
                warnings.append(f'PDF page {number}: little/no extracted text; OCR or visual review may be needed.')
            pages.append(Page(number, labels[number-1], text))
            if number % 100 == 0 or number == total:
                print(f'Extracted {number}/{total} PDF pages', file=sys.stderr, flush=True)
        if not any(len(page.text) >= 30 for page in pages):
            raise NeedsOCR('No usable PDF text. OCR required before vectorisation.')
        if capture.count:
            warnings.append(f'PDF parser produced {capture.count} warnings; diagnostic samples follow.')
            warnings.extend(capture.samples)
        return title, author, pages, warnings
    finally:
        logger.removeHandler(capture)
        logger.propagate = previous_propagation
        logger.setLevel(previous_level)
