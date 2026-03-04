from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PROJECT = ROOT / "apps" / "api"
if str(API_PROJECT) not in sys.path:
    sys.path.insert(0, str(API_PROJECT))

from app.extract.extractor import chunk_passages, extract_document


class ExtractorTests(unittest.TestCase):
    def test_extract_document_fallback_parses_text_and_title(self) -> None:
        html = """
        <html>
          <head><title>Sample Title</title></head>
          <body>
            <article><h1>Hello</h1><p>World</p><p>Second paragraph.</p></article>
          </body>
        </html>
        """
        result = extract_document(html, max_chars=1000)

        self.assertEqual(result.title, "Sample Title")
        self.assertIn("Hello", result.markdown)
        self.assertIn("World", result.markdown)
        self.assertIsNotNone(result.content_hash)
        self.assertEqual(len(result.content_hash or ""), 64)

    def test_chunk_passages_splits_long_content(self) -> None:
        markdown = "\n\n".join([f"paragraph {i} " + ("x" * 120) for i in range(20)])
        passages = chunk_passages(markdown, chunk_size=300, overlap=50)

        self.assertGreater(len(passages), 1)
        for passage in passages:
            self.assertLessEqual(len(passage), 300)


if __name__ == "__main__":
    unittest.main()
