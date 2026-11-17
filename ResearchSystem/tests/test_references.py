import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from book_research.presentation import citation, readable_metadata


class ReferenceTests(unittest.TestCase):
    def test_production_metadata_falls_back_without_inventing_author(self):
        title, author = readable_metadata('1234_1_En_Print.indd', '0014323', 'A Readable Book Title.pdf')
        self.assertEqual((title, author), ('A Readable Book Title', ''))
        title, _ = readable_metadata('[Example_Author]_Example_Title 2026-01-02 01_02_03', '',
                                    '[Example_Author]_Example_Title 2026-01-02 01_02_03.pdf')
        self.assertEqual(title, 'Example Title')

    def test_pdf_reference_uses_file_page_without_claiming_printed_label(self):
        row = dict(title='Example Physics', author='A. Example', filename='book.pdf',
                   page=104, page_label='96', section='', text='Gravity.')
        ref = citation(row)
        self.assertEqual(ref['reference'], 'A. Example, Example Physics, PDF p. 104')
        self.assertEqual(ref['location_kind'], 'pdf_file_page')
        self.assertNotIn('96', ref['reference'])

    def test_epub_reference_uses_actual_heading_and_hides_archive_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'book.epub'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('OEBPS/xhtml/chapter.xhtml', '<html><body><p>Chapter 3</p><p>Lorentz Transformation</p><p>Example content.</p></body></html>')
            row = dict(title='Relativity', author='A. Example', filename='book.epub',
                       page=13, page_label='spine-13', section='OEBPS/xhtml/chapter.xhtml',
                       text='3.3. Simple Applications\nExample explanation.')
            ref = citation(row, path)
            self.assertIn('Chapter 3: Lorentz Transformation', ref['reference'])
            self.assertIn('section 3.3 Simple Applications', ref['reference'])
            self.assertNotIn('OEBPS', json.dumps(ref))
            self.assertNotIn('spine-', json.dumps(ref))
            self.assertNotIn(str(path), json.dumps(ref))
            row['section'] = 'missing.xhtml'
            self.assertTrue(citation(row, path)['location'].startswith('Section 13'))
