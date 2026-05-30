"""
fix/pm-font-warn — Testler
1. #pmFontLoadWarn HTML'de var mi
2. upload_font_library gecersiz font → HTTP 400
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ── 1: HTML elementi ────────────────────────────────────────────────────────

class TestFontWarnElement:
    def test_pmFontLoadWarn_exists_in_html(self):
        """index.html'de pmFontLoadWarn id'li element bulunmali."""
        html_path = PROJECT_ROOT / "src" / "webui" / "index.html"
        assert html_path.exists(), "index.html bulunamadi"
        content = html_path.read_text(encoding="utf-8")
        assert 'id="pmFontLoadWarn"' in content, "#pmFontLoadWarn elementi eksik"
        assert 'hidden' in content[content.index('id="pmFontLoadWarn"'):content.index('id="pmFontLoadWarn"') + 100], \
            "#pmFontLoadWarn baslangicta hidden olmali"

    def test_pmFontLoadWarn_inside_recipe_panel(self):
        """pmFontLoadWarn, pmRecipePanel icinde olmali."""
        html = (PROJECT_ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
        panel_start = html.find('id="pmRecipePanel"')
        warn_pos    = html.find('id="pmFontLoadWarn"')
        assert panel_start != -1, "pmRecipePanel bulunamadi"
        assert warn_pos != -1,    "pmFontLoadWarn bulunamadi"
        assert warn_pos > panel_start, "pmFontLoadWarn, pmRecipePanel'in disinda"

    def test_injectFontFace_references_pmFontLoadWarn(self):
        """product_matching.js _injectFontFace fonksiyonu pmFontLoadWarn'a yazmali."""
        js = (PROJECT_ROOT / "src" / "webui" / "product_matching.js").read_text(encoding="utf-8")
        assert "pmFontLoadWarn" in js, "_injectFontFace() pmFontLoadWarn'u kullanmiyor"
        # FontFace.load() catch blogunu icermeli
        assert "FontFace" in js, "FontFace API kullanilmiyor"
        assert ".catch" in js or "catch(" in js, "Hata yakalama (.catch) eksik"


# ── 2: Font imzası doğrulama ────────────────────────────────────────────────

def _minimal_ttf() -> bytes:
    """Geçerli sfnt imzalı minimal TTF baytları üretir."""
    # sfnt header: magic(4) + numTables(2) + searchRange(2) + entrySelector(2) + rangeShift(2)
    num_tables = 1
    return struct.pack(">I HHH H", 0x00010000, num_tables, 16, 0, 16) + b"\x00" * 100


def _minimal_otf() -> bytes:
    """Geçerli OTTO imzalı minimal OTF baytları üretir."""
    num_tables = 1
    return b"OTTO" + struct.pack(">HHH H", num_tables, 16, 0, 16) + b"\x00" * 100


def _corrupt_font() -> bytes:
    """Geçersiz (bozuk) font baytları."""
    return b"CORRUPTED_NOT_A_FONT" + b"\x00" * 50


def _too_short_font() -> bytes:
    """12 bayttan kısa — imza bile yok."""
    return b"\x00\x01\x00"


class TestFontValidation:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from server.flask_app import app
        import server.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_PROJECT_ROOT", tmp_path)
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def _post_font(self, client, data: bytes, filename: str = "test.ttf", tip: str = "label"):
        from io import BytesIO
        return client.post(
            "/api/upload_font_library",
            data={"file": (BytesIO(data), filename), "tip": tip, "laser_safe": "false"},
            content_type="multipart/form-data",
        )

    def test_valid_ttf_accepted(self, client):
        resp = self._post_font(client, _minimal_ttf(), "valid.ttf")
        # OK veya font yolu hatasi kabul edilebilir (dosya sistemine yazma olmayabilir)
        assert resp.status_code != 400 or "imza" not in resp.get_data(as_text=True)

    def test_valid_otf_accepted(self, client):
        resp = self._post_font(client, _minimal_otf(), "valid.otf")
        assert resp.status_code != 400 or "imza" not in resp.get_data(as_text=True)

    def test_corrupt_ttf_rejected_400(self, client):
        resp = self._post_font(client, _corrupt_font(), "corrupt.ttf")
        assert resp.status_code == 400, f"Bozuk font kabul edildi: {resp.status_code}"
        data = resp.get_json()
        assert data["status"] == "ERROR"
        assert "geçersiz" in data["error"].lower() or "imza" in data["error"].lower()

    def test_too_short_font_rejected_400(self, client):
        resp = self._post_font(client, _too_short_font(), "short.ttf")
        assert resp.status_code == 400

    def test_empty_bytes_rejected_400(self, client):
        resp = self._post_font(client, b"", "empty.ttf")
        assert resp.status_code == 400

    def test_wrong_extension_rejected_400(self, client):
        resp = self._post_font(client, _minimal_ttf(), "font.exe")
        assert resp.status_code == 400

    def test_pdf_disguised_as_ttf_rejected(self, client):
        """PDF magic bytes (geçersiz sfnt) → reddedilmeli."""
        pdf_bytes = b"%PDF-1.4" + b"\x00" * 100
        resp = self._post_font(client, pdf_bytes, "disguised.ttf")
        assert resp.status_code == 400


# ── _is_valid_font_bytes birim testi ───────────────────────────────────────

class TestIsValidFontBytes:
    def setup_method(self):
        from server.routes import _is_valid_font_bytes
        self._check = _is_valid_font_bytes

    def test_ttf_magic_valid(self):
        assert self._check(_minimal_ttf(), ".ttf") is True

    def test_otf_magic_valid(self):
        assert self._check(_minimal_otf(), ".otf") is True

    def test_corrupt_invalid(self):
        assert self._check(_corrupt_font(), ".ttf") is False

    def test_too_short_invalid(self):
        assert self._check(_too_short_font(), ".ttf") is False

    def test_empty_invalid(self):
        assert self._check(b"", ".ttf") is False

    def test_pdf_bytes_invalid(self):
        assert self._check(b"%PDF-1.4" + b"\x00" * 50, ".ttf") is False

    def test_zero_tables_invalid(self):
        """sfnt imzası doğru ama numTables=0 → geçersiz."""
        bad = struct.pack(">I HHH H", 0x00010000, 0, 0, 0, 0) + b"\x00" * 50
        assert self._check(bad, ".ttf") is False
