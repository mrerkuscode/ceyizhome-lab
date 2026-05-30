"""Tests for font_library_api, recipe_api and new Flask routes.

Run: pytest tests/test_recipe_font_api.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure src/ is on path
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def root(tmp_path):
    """Create a minimal project root with required dirs."""
    (tmp_path / "data").mkdir()
    (tmp_path / "config" / "fonts").mkdir(parents=True)
    (tmp_path / "assets" / "fonts" / "library").mkdir(parents=True)
    return tmp_path


# ── Font library API ─────────────────────────────────────────────────────────

class TestFontLibraryApi:
    def test_list_fonts_empty(self, root):
        from webui_backend.font_library_api import list_fonts
        result = list_fonts(root)
        assert result["label_fonts"] == []
        assert result["laser_fonts"] == []

    def test_add_and_list_label_font(self, root):
        from webui_backend.font_library_api import add_font, list_fonts
        fake_bytes = b"\x00\x01\x02" * 20  # minimal fake TTF
        r = add_font(root, "TestLabel.ttf", fake_bytes, "label")
        assert r["status"] == "OK"
        assert r["font_type"] == "label"
        manifest = list_fonts(root)
        assert len(manifest["label_fonts"]) == 1
        assert manifest["label_fonts"][0]["name"] == "TestLabel"

    def test_add_laser_font_with_laser_safe(self, root):
        from webui_backend.font_library_api import add_font, list_fonts
        fake_bytes = b"\x00\x01\x02" * 20
        r = add_font(root, "LaserTest.otf", fake_bytes, "laser", laser_safe=True)
        assert r["status"] == "OK"
        manifest = list_fonts(root)
        laser = manifest["laser_fonts"]
        assert len(laser) == 1
        assert laser[0]["laser_safe"] is True

    def test_add_invalid_type_rejected(self, root):
        from webui_backend.font_library_api import add_font
        r = add_font(root, "Bad.ttf", b"\x00" * 20, "invalid_type")
        assert r["status"] == "ERROR"

    def test_add_invalid_extension_rejected(self, root):
        from webui_backend.font_library_api import add_font
        r = add_font(root, "Bad.exe", b"\x00" * 20, "label")
        assert r["status"] == "ERROR"

    def test_delete_font(self, root):
        from webui_backend.font_library_api import add_font, delete_font, list_fonts
        fake_bytes = b"\x00\x01\x02" * 20
        added = add_font(root, "ToDelete.ttf", fake_bytes, "label")
        font_id = added["font"]["id"]
        r = delete_font(root, font_id)
        assert r["status"] == "OK"
        manifest = list_fonts(root)
        assert all(f["id"] != font_id for f in manifest["label_fonts"])

    def test_delete_missing_font(self, root):
        from webui_backend.font_library_api import delete_font
        r = delete_font(root, "nonexistent-id")
        assert r["status"] == "MISSING"


# ── Recipe API ───────────────────────────────────────────────────────────────

class TestRecipeApi:
    def _make_label_font(self, root, name="TestFont"):
        from webui_backend.font_library_api import add_font
        r = add_font(root, f"{name}.ttf", b"\x00\x01\x02" * 20, "label")
        return r["font"]["id"]

    def _make_laser_font(self, root, name="LazerFont", safe=True):
        from webui_backend.font_library_api import add_font
        r = add_font(root, f"{name}.ttf", b"\x00\x01\x02" * 20, "laser", laser_safe=safe)
        return r["font"]["id"]

    def test_get_recipe_missing_returns_empty(self, root):
        from webui_backend.recipe_api import get_recipe
        r = get_recipe(root, "BARKOD123")
        assert r["has_recipe"] is False
        assert r["slots"] == []

    def test_save_and_get_recipe(self, root):
        from webui_backend.recipe_api import save_recipe, get_recipe
        font_id = self._make_label_font(root)
        slots = [{"id": "s1", "konum": "Kurdele", "cikti": "etiket", "besleyen": "isim", "font_id": font_id, "adet": 60}]
        r = save_recipe(root, "BARKOD001", slots)
        assert r["status"] == "OK"
        got = get_recipe(root, "BARKOD001")
        assert got["has_recipe"] is True
        assert len(got["slots"]) == 1

    def test_save_recipe_requires_slot(self, root):
        from webui_backend.recipe_api import save_recipe
        r = save_recipe(root, "BARKOD002", [])
        assert r["status"] == "ERROR"

    def test_save_recipe_invalid_cikti(self, root):
        from webui_backend.recipe_api import save_recipe
        slots = [{"id": "s1", "konum": "Test", "cikti": "invalid", "besleyen": "isim", "adet": 1}]
        r = save_recipe(root, "BARKOD003", slots)
        assert r["status"] == "ERROR"

    def test_save_recipe_laser_slot_requires_laser_safe_font(self, root):
        from webui_backend.recipe_api import save_recipe
        unsafe_id = self._make_laser_font(root, name="Unsafe", safe=False)
        slots = [{"id": "s1", "konum": "Lazer", "cikti": "lazer", "besleyen": "isim", "font_id": unsafe_id, "adet": 1}]
        r = save_recipe(root, "BARKOD004", slots)
        assert r["status"] == "ERROR"
        assert "lazer-güvenli" in r["error"].lower() or "güvenli" in r["error"]

    def test_save_recipe_laser_slot_with_laser_safe_font_ok(self, root):
        from webui_backend.recipe_api import save_recipe
        safe_id = self._make_laser_font(root, name="SafeFont", safe=True)
        slots = [{"id": "s1", "konum": "Lazer", "cikti": "lazer", "besleyen": "isim", "font_id": safe_id, "adet": 1}]
        r = save_recipe(root, "BARKOD005", slots)
        assert r["status"] == "OK"

    def test_save_recipe_laser_slot_no_font_ok(self, root):
        """Laser slot without font_id should be allowed (font optional at save time)."""
        from webui_backend.recipe_api import save_recipe
        slots = [{"id": "s1", "konum": "Lazer", "cikti": "lazer", "besleyen": "isim", "font_id": "", "adet": 1}]
        r = save_recipe(root, "BARKOD006", slots)
        assert r["status"] == "OK"

    def test_recipe_barcode_persistence(self, root):
        """Saving a second recipe does not overwrite the first."""
        from webui_backend.recipe_api import save_recipe, get_recipe
        font_id = self._make_label_font(root)
        save_recipe(root, "BAR001", [{"id": "s1", "konum": "A", "cikti": "etiket", "besleyen": "isim", "font_id": font_id, "adet": 1}])
        save_recipe(root, "BAR002", [{"id": "s1", "konum": "B", "cikti": "etiket", "besleyen": "tarih", "font_id": font_id, "adet": 2}])
        assert get_recipe(root, "BAR001")["has_recipe"] is True
        assert get_recipe(root, "BAR002")["has_recipe"] is True
        assert get_recipe(root, "BAR001")["slots"][0]["konum"] == "A"


# ── Bulk apply ───────────────────────────────────────────────────────────────

class TestBulkApply:
    def test_bulk_apply_creates_default_slot(self, root):
        from webui_backend.recipe_api import bulk_apply_recipe, get_recipe
        r = bulk_apply_recipe(root, ["BULK001", "BULK002"], {"adet": 30})
        assert r["status"] == "OK"
        assert len(r["updated"]) == 2
        r1 = get_recipe(root, "BULK001")
        assert r1["has_recipe"] is True
        assert r1["slots"][0]["adet"] == 30

    def test_bulk_apply_merges_cikti(self, root):
        from webui_backend.recipe_api import bulk_apply_recipe, get_recipe, save_recipe
        # Pre-create recipe with etiket slot
        save_recipe(root, "MERGE001", [{"id": "s1", "konum": "K", "cikti": "etiket", "besleyen": "isim", "adet": 10}])
        bulk_apply_recipe(root, ["MERGE001"], {"cikti": "lazer"})
        r = get_recipe(root, "MERGE001")
        assert r["slots"][0]["cikti"] == "lazer"

    def test_bulk_apply_empty_barkodlar(self, root):
        from webui_backend.recipe_api import bulk_apply_recipe
        r = bulk_apply_recipe(root, [], {"adet": 5})
        assert r["status"] == "ERROR"


# ── Trendyol catalog sync (mocked) ──────────────────────────────────────────

class TestTrendyolProductSync:
    def test_sync_products_config_missing(self, root):
        """sync_products returns CONFIG_MISSING when no credentials are set."""
        from webui_backend.trendyol_api import sync_products
        r = sync_products(root)
        assert r["status"] == "CONFIG_MISSING"
        assert r["count"] == 0

    def test_sync_products_writes_catalog(self, root, monkeypatch):
        """sync_products writes barkod-keyed JSON when fetch_products succeeds."""
        fake_products = [
            {"barcode": "BAR_A", "title": "Ürün A", "stockCode": "SKU001", "images": [{"url": "http://img.example.com/a.jpg"}], "onSale": "true"},
            {"barcode": "BAR_B", "title": "Ürün B", "stockCode": "SKU002", "images": [], "onSale": "false"},
        ]

        import webui_backend.trendyol_api as ta

        def fake_is_configured(_root):
            return True

        def fake_get_settings(_root, **kwargs):
            return {"supplier_id": "123", "api_key": "k", "api_secret": "s", "stage": False}

        def fake_credential_problem(_settings):
            return None

        def fake_fetch_products(_root, **kwargs):
            return fake_products

        monkeypatch.setattr(ta, "is_configured", fake_is_configured)
        monkeypatch.setattr(ta, "get_settings", fake_get_settings)
        monkeypatch.setattr(ta, "_credential_configuration_problem", fake_credential_problem)
        monkeypatch.setattr(ta, "fetch_products", fake_fetch_products)

        r = ta.sync_products(root)
        assert r["status"] == "OK"
        assert r["count"] == 2
        catalog_path = root / "data" / "trendyol_products.json"
        assert catalog_path.exists()
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        assert "BAR_A" in catalog
        assert catalog["BAR_A"]["title"] == "Ürün A"
        assert "BAR_B" in catalog


# ── Flask route smoke tests ──────────────────────────────────────────────────

class TestFlaskRoutes:
    @pytest.fixture()
    def client(self, root, monkeypatch):
        """Create a Flask test client with PROJECT_ROOT pointing to tmp root."""
        import server.routes as routes_module
        monkeypatch.setattr(routes_module, "_PROJECT_ROOT", root)
        from server.flask_app import app
        app.config["TESTING"] = True
        return app.test_client()

    def test_get_fonts_endpoint(self, client):
        r = client.get("/api/fonts")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "label_fonts" in data

    def test_get_recipe_endpoint_empty(self, client):
        r = client.get("/api/recipe/TESTBARKOD")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["has_recipe"] is False

    def test_save_and_get_recipe_endpoint(self, client, root):
        # First add a label font so we have a valid font_id
        from webui_backend.font_library_api import add_font
        added = add_font(root, "Test.ttf", b"\x00\x01" * 30, "label")
        font_id = added["font"]["id"]

        payload = {
            "barkod": "E2E001",
            "slots": [{"id": "s1", "konum": "Kurdele", "cikti": "etiket", "besleyen": "isim", "font_id": font_id, "adet": 60}],
        }
        r = client.post("/api/save_recipe", json=payload)
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "OK"

        r2 = client.get("/api/recipe/E2E001")
        data2 = json.loads(r2.data)
        assert data2["has_recipe"] is True

    def test_bulk_apply_endpoint(self, client):
        payload = {
            "barkodlar": ["B001", "B002"],
            "ayarlar": {"cikti": "etiket", "adet": 10},
        }
        r = client.post("/api/bulk_apply_recipe", json=payload)
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "OK"
        assert len(data["updated"]) == 2

    def test_trendyol_products_endpoint(self, client, root):
        (root / "data" / "trendyol_products.json").write_text(
            json.dumps({"BAR1": {"barkod": "BAR1", "title": "Test", "model_code": "M1", "image_url": "", "sale_status": "true", "synced_at": "2026-05-30 00:00:00"}}),
            encoding="utf-8",
        )
        r = client.get("/api/trendyol_products")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert isinstance(data, list)
        assert data[0]["barkod"] == "BAR1"
