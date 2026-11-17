import logging
import unittest

from book_research.pdf_extract import PDFDiagnostics


class PDFDiagnosticTests(unittest.TestCase):
    def test_repeated_font_diagnostics_are_bounded_without_losing_count(self):
        capture = PDFDiagnostics()
        for number in range(1000):
            capture.handle(logging.LogRecord('pypdf', logging.WARNING, '', 0,
                'Font parsing warning %s: ' + 'x'*1000, (number,), None))
        self.assertEqual(capture.count, 1000)
        self.assertEqual(len(capture.samples), 3)
        self.assertTrue(all(len(sample) <= 250 for sample in capture.samples))
