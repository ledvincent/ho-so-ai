import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from hoso_ai.fetch import capture, form_extension, inspect_page, official_url

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.004194"


class FetchTests(unittest.TestCase):
    def test_rejects_app_shell_even_with_procedure_code_in_script(self):
        with self.assertRaises(ValueError):
            inspect_page(b'<h1>Portal</h1><script>1.004194</script>', URL, "Đăng ký tạm trú", "1.004194")

    def test_real_saved_pages_keep_both_form_versions_and_legal_basis(self):
        by_code = inspect_page((FIXTURES / "registration_by_code.html").read_bytes(), URL, "Đăng ký tạm trú", "1.004194")
        detail = inspect_page((FIXTURES / "registration_detail.html").read_bytes(), URL, "Đăng ký tạm trú", "1.004194", detail=True)
        self.assertEqual(len(by_code["form_links"]), 3)
        self.assertTrue(all("_66" in link["label"] for link in by_code["form_links"]))
        self.assertTrue(any("53" in link["label"] for link in detail["unresolved_form_links"]))
        self.assertIn("53/2025/TT-BCA", {row["number"] for row in detail["legal_basis"]})
        self.assertIn("Trình tự thực hiện", detail["missing_sections"])
        with self.assertRaises(ValueError):
            inspect_page((FIXTURES / "registration_detail.html").read_bytes(), URL, "Đăng ký tạm trú", "9.999999", detail=True)

    def test_rejects_external_or_insecure_urls(self):
        for url in ["http://csdl.dichvucong.gov.vn/a", "https://example.org/a", "https://vpcp.dichvucong.gov.vn.evil.test/a", "https://user@vpcp.dichvucong.gov.vn/a"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                official_url(url)

    def test_html_and_arbitrary_zips_are_not_forms(self):
        with self.assertRaises(ValueError):
            form_extension(b"<html>Service unavailable</html>")
        body = BytesIO()
        with ZipFile(body, "w") as archive:
            archive.writestr("unrelated.txt", "hello")
        with self.assertRaises(ValueError):
            form_extension(body.getvalue())
        self.assertEqual(form_extension(bytes.fromhex("D0CF11E0A1B11AE1") + b"fake test document"), ".doc")

    def test_form_failure_is_recorded_and_capture_stays_draft(self):
        class FakeDownloader:
            def get(self, url):
                if "download_file" in url:
                    raise OSError("simulated 503")
                filename = "registration_detail.html" if "hanh-chinh-chi-tiet" in url else "registration_by_code.html"
                body = (FIXTURES / filename).read_bytes()
                return body, {"source_url": url, "resolved_url": url, "fetched_at": "2026-10-31T00:00:00+00:00", "sha256": hashlib.sha256(body).hexdigest()}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = capture({"code": "1.004194", "name": "Đăng ký tạm trú"}, root, FakeDownloader())
            self.assertEqual(report["review_status"], "draft")
            self.assertEqual(len(report["pages"]), 2)
            self.assertEqual(len(report["errors"]), 3)
            self.assertEqual(report["forms"], [])
            for page in report["pages"]:
                self.assertEqual(hashlib.sha256((root / page["raw_path"]).read_bytes()).hexdigest(), page["sha256"])
            self.assertEqual(json.loads((root / "captures/1.004194.json").read_text(encoding="utf-8"))["review_status"], "draft")


if __name__ == "__main__":
    unittest.main()
