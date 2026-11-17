import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from book_research.core import Catalogue, NeedsOCR, Page, chunks, extract, subjects


class FakeEmbeddings:
    """Deterministic test double; never reported as real semantic performance."""
    model = 'test-double'

    def identity(self):
        return 'test-double@v1'

    def embed(self, texts):
        return [[float('reaction' in text.lower() or 'chemistry' in text.lower()),
                 float('photon' in text.lower() or 'quantum' in text.lower()), 0.1] for text in texts]


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db_path = self.root / 'catalogue.sqlite3'
        self.catalogue = Catalogue(self.db_path)

    def tearDown(self):
        self.catalogue.close()
        self.temp.cleanup()

    def book(self, name, text):
        path = self.root / name
        path.write_text(text, encoding='utf-8')
        return path

    def test_import_duplicate_preserves_source_and_registers_alias(self):
        source = self.book('a.txt', 'A chemical reaction involves molecules and chemistry.')
        before = source.read_bytes()
        self.assertEqual(self.catalogue.ingest(source)['status'], 'imported')
        alias = self.root / 'duplicate.txt'
        alias.write_bytes(before)
        self.assertEqual(self.catalogue.ingest(alias)['status'], 'duplicate')
        self.assertEqual(len(self.catalogue.catalogue()), 1)
        self.assertEqual(self.catalogue.db.execute('SELECT count(*) FROM sources').fetchone()[0], 2)
        self.assertEqual(source.read_bytes(), before)

    def test_cross_subject_tags_and_filtered_retrieval(self):
        self.catalogue.ingest(self.book('mixed.txt', 'Quantum mechanics uses a mathematical equation.'))
        hit = self.catalogue.search('quantum', subject='mathematics')['results'][0]
        self.assertEqual(set(hit['tags']), {'physics','mathematics'})
        self.assertEqual(hit['tag_status'], 'unreviewed')
        self.assertEqual(self.catalogue.search('quantum', subject='biology')['results'], [])

    def test_keyword_ranking_and_empty_results(self):
        self.catalogue.ingest(self.book('biology.txt', 'Genetics and protein support cell biology.'))
        self.catalogue.ingest(self.book('chemistry.txt', 'A catalyst affects a chemical reaction.'))
        result = self.catalogue.search('catalyst reaction')
        self.assertEqual(result['mode'], 'keyword-only')
        self.assertEqual(result['results'][0]['title'], 'chemistry')
        self.assertEqual(self.catalogue.search('nonexistentword')['results'], [])

    def test_page_context_and_no_local_path_disclosure(self):
        self.catalogue.ingest(self.book('pages.txt', 'first photon page\fsecond quantum page\fthird equation page'))
        hit = self.catalogue.search('quantum')['results'][0]
        fetched = self.catalogue.fetch(hit['id'])
        self.assertEqual({item['page'] for item in fetched['content']}, {1,2,3})
        self.assertNotIn(str(self.root), json.dumps(fetched))
        self.assertNotIn(str(self.root), json.dumps(self.catalogue.catalogue()))

    def test_readonly_database_cannot_write(self):
        source = self.book('a.txt', 'quantum equation')
        self.catalogue.ingest(source)
        readonly = Catalogue(self.db_path, readonly=True)
        try:
            self.assertTrue(readonly.search('quantum')['results'])
            with self.assertRaises(ValueError):
                readonly.ingest(source)
            with self.assertRaises(Exception):
                readonly.db.execute("DELETE FROM books")
        finally:
            readonly.close()

    def test_real_vector_path_with_explicit_test_double(self):
        self.catalogue.embeddings = FakeEmbeddings()
        self.catalogue.ingest(self.book('a.txt', 'chemistry reaction'))
        self.catalogue.ingest(self.book('b.txt', 'photon quantum'))
        result = self.catalogue.search('chemical reaction')
        self.assertEqual(result['mode'], 'hybrid')
        self.assertEqual(result['results'][0]['title'], 'a')
        self.assertEqual(self.catalogue.catalogue()[0]['embedded_passages'], 1)
        with self.assertRaises(ValueError):
            self.catalogue._check_dimensions([[1,2]])

    def test_changed_embedding_model_fails_closed(self):
        self.catalogue.embeddings = FakeEmbeddings()
        self.catalogue.ingest(self.book('a.txt', 'chemistry reaction'))
        self.catalogue.embeddings.identity = lambda: 'another-model@v2'
        with self.assertRaises(ValueError):
            self.catalogue.search('chemistry')

    def test_chunk_boundaries_overlap_and_validation(self):
        text = ' '.join(str(i) for i in range(1000))
        result = list(chunks(text, 350, 50))
        self.assertEqual(result[0].split()[-50:], result[1].split()[:50])
        self.assertEqual(result[-1].split()[-1], '999')
        with self.assertRaises(ValueError):
            list(chunks(text, 50, 50))

    def test_limits_and_invalid_ids(self):
        for value in [0,21]:
            with self.assertRaises(ValueError):
                self.catalogue.search('a', limit=value)
        with self.assertRaises(ValueError):
            self.catalogue.search('a', subject='made-up')
        with self.assertRaises(ValueError):
            self.catalogue.fetch('99999')
        self.assertEqual(self.catalogue.search('" OR DROP TABLE books; --')['results'], [])

    def test_epub_spine_order_and_locations(self):
        path = self.root / 'test.epub'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="OEBPS/book.opf"/></rootfiles></container>')
            archive.writestr('OEBPS/book.opf', '<package xmlns="urn:test" xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Test title</dc:title></metadata><manifest><item id="b" href="second.xhtml"/><item id="a" href="first.xhtml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
            archive.writestr('OEBPS/first.xhtml', '<html><body>First quantum chapter</body></html>')
            archive.writestr('OEBPS/second.xhtml', '<html><body>Second chemistry chapter</body></html>')
        title, _, pages, warnings = extract(path)
        self.assertEqual(title, 'Test title')
        self.assertIn('First', pages[0].text)
        self.assertEqual(pages[1].label, 'spine-2')
        self.assertTrue(warnings)

    def test_pdf_text_page_provenance_and_scan_detection(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        path = self.root / 'text.pdf'
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 72 700 Td (Quantum mechanics uses mathematics and an equation.) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        writer.write(path)
        result = self.catalogue.ingest(path)
        self.assertEqual(result['status'], 'imported')
        hit = self.catalogue.search('Quantum')['results'][0]
        self.assertEqual(hit['page'], 1)
        scan = self.root / 'scan.pdf'
        blank = PdfWriter()
        blank.add_blank_page(width=612, height=792)
        blank.write(scan)
        with self.assertRaises(NeedsOCR):
            extract(scan)


if __name__ == '__main__':
    unittest.main()
