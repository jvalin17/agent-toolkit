"""Tests for skills/updater/scripts/check-links.py — URL extraction.

Covers: fenced code block skipping, normal URL extraction, edge cases.
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path so we can import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "updater" / "scripts"))
from importlib import import_module

check_links = import_module("check-links")
extract_urls = check_links.extract_urls


@pytest.fixture
def md_file(tmp_path):
    """Helper that writes content to a temp .md file and returns its path."""
    def _write(content):
        p = tmp_path / "test.md"
        p.write_text(content, encoding="utf-8")
        return str(p)
    return _write


class TestExtractUrls:
    def test_extracts_normal_urls(self, md_file):
        path = md_file("See [example](https://example.com) for details.\n")
        urls = extract_urls(path)
        assert len(urls) == 1
        assert urls[0][0] == "https://example.com"

    def test_skips_urls_inside_fenced_code_block(self, md_file):
        content = (
            "# Dockerfile\n"
            "\n"
            "```dockerfile\n"
            "HEALTHCHECK CMD curl -f http://localhost:8040/health || exit 1\n"
            "```\n"
            "\n"
            "Real link: https://example.com\n"
        )
        path = md_file(content)
        urls = extract_urls(path)
        extracted = [u[0] for u in urls]
        assert "http://localhost:8040/health" not in extracted
        assert "https://example.com" in extracted

    def test_skips_urls_in_backtick_block_without_language(self, md_file):
        content = (
            "```\n"
            "curl http://localhost:3000/api\n"
            "```\n"
        )
        path = md_file(content)
        urls = extract_urls(path)
        assert len(urls) == 0

    def test_extracts_multiple_urls_from_prose(self, md_file):
        content = (
            "- [A](https://a.com)\n"
            "- [B](https://b.com)\n"
        )
        path = md_file(content)
        urls = extract_urls(path)
        assert len(urls) == 2

    def test_handles_multiple_code_blocks(self, md_file):
        content = (
            "Real: https://real.com\n"
            "```\n"
            "http://skip1.com\n"
            "```\n"
            "Also real: https://also-real.com\n"
            "```bash\n"
            "http://skip2.com\n"
            "```\n"
            "Final: https://final.com\n"
        )
        path = md_file(content)
        extracted = [u[0] for u in extract_urls(path)]
        assert "https://real.com" in extracted
        assert "https://also-real.com" in extracted
        assert "https://final.com" in extracted
        assert "http://skip1.com" not in extracted
        assert "http://skip2.com" not in extracted
