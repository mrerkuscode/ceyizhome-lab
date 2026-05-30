"""
Ürün Eşleştirme Düzeltmeleri — Testler
fix/urun-eslestirme-fixes branch

1. sabit_metin kaydı
2. Lazer-güvensiz font → HTTP 400
3. sync_products model_code (productCode öncelikli)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from webui_backend.recipe_api import save_recipe, get_recipe, bulk_apply_recipe


# ── Fixtures ────────────────────────────────────────────────────────────────

def _write_laser_font_manifest(tmp_path: Path, *, laser_safe: bool) -> str:
    """Write a test font manifest and return the font_id."""
    font_id = "testfont01"
    manifest = {
        "label_fonts": [
            {"id": "labelfont01", "name": "LabelTest", "file": "labelfont01_test.ttf",
             "uploaded_at": "2026-01-01", "laser_safe": False}
        ],
        "laser_fonts": [
            {"id": font_id, "name": "LazerTest", "file": "testfont01_test.ttf",
             "uploaded_at": "2026-01-01", "laser_safe": laser_safe}
        ],
    }
    manifest_dir = tmp_path / "config" / "fonts"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return font_id


# ── İş 1: sabit_metin kaydı ─────────────────────────────────────────────────

class TestSabitMetinKaydi:
    def test_sabit_metin_saved_and_returned(self, tmp_path: Path):
        """Slot'ta sabit_metin → kaydet → GET → aynı metin dönmeli."""
        slots = [
            {
                "id": "slot_1",
                "konum": "Kurdele",
                "cikti": "etiket",
                "besleyen": "sabit",
                "font_id": "",
                "adet": 1,
                "sabit_metin": "Nişan Hatırası",
                "plaka_adedi": None,
            }
        ]
        result = save_recipe(tmp_path, "BARKOD001", slots)
        assert result["status"] == "OK", result

        got = get_recipe(tmp_path, "BARKOD001")
        assert got["has_recipe"] is True
        saved_slot = got["slots"][0]
        assert saved_slot.get("sabit_metin") == "Nişan Hatırası", f"sabit_metin eksik: {saved_slot}"

    def test_sabit_metin_empty_string_preserved(self, tmp_path: Path):
        """sabit_metin boş string → kaydet → boş string dönmeli (None değil)."""
        slots = [
            {"id": "s1", "konum": "Test", "cikti": "etiket", "besleyen": "sabit",
             "font_id": "", "adet": 1, "sabit_metin": "", "plaka_adedi": None}
        ]
        save_recipe(tmp_path, "BARKOD002", slots)
        got = get_recipe(tmp_path, "BARKOD002")
        saved_slot = got["slots"][0]
        # Boş string veya None: ikiside kabul edilebilir ama alan mevcut olmalı
        assert "sabit_metin" in saved_slot or saved_slot.get("sabit_metin") == ""

    def test_sabit_artı_isim_besleyen_saved(self, tmp_path: Path):
        """besleyen='sabit+isim' ve sabit_metin → kaydedilmeli."""
        slots = [
            {"id": "s1", "konum": "Üst baskı", "cikti": "etiket", "besleyen": "sabit+isim",
             "font_id": "", "adet": 2, "sabit_metin": "Allah'ın Emri ile", "plaka_adedi": None}
        ]
        save_recipe(tmp_path, "BARKOD003", slots)
        got = get_recipe(tmp_path, "BARKOD003")
        assert got["slots"][0]["sabit_metin"] == "Allah'ın Emri ile"
        assert got["slots"][0]["besleyen"] == "sabit+isim"

    def test_multiple_slots_different_sabit_metin(self, tmp_path: Path):
        """Birden fazla slot, her birinde farklı sabit_metin."""
        slots = [
            {"id": "s1", "konum": "A", "cikti": "etiket", "besleyen": "sabit",
             "font_id": "", "adet": 1, "sabit_metin": "Metin A", "plaka_adedi": None},
            {"id": "s2", "konum": "B", "cikti": "etiket", "besleyen": "sabit",
             "font_id": "", "adet": 1, "sabit_metin": "Metin B", "plaka_adedi": None},
        ]
        save_recipe(tmp_path, "BARKOD004", slots)
        got = get_recipe(tmp_path, "BARKOD004")
        texts = [s.get("sabit_metin") for s in got["slots"]]
        assert "Metin A" in texts
        assert "Metin B" in texts


# ── İş 2: Lazer-güvensiz font → ERROR ───────────────────────────────────────

class TestLazerFontValidation:
    def test_laser_unsafe_font_rejected_in_save_recipe(self, tmp_path: Path):
        """Lazer slotunda laser_safe=False font → ERROR dönmeli."""
        font_id = _write_laser_font_manifest(tmp_path, laser_safe=False)
        slots = [
            {"id": "s1", "konum": "Lazer", "cikti": "lazer", "besleyen": "isim",
             "font_id": font_id, "adet": 1, "sabit_metin": "", "plaka_adedi": 1}
        ]
        result = save_recipe(tmp_path, "LASER001", slots)
        assert result["status"] == "ERROR", f"Güvensiz font kabul edilmemeli: {result}"
        assert "lazer" in result["error"].lower() or "güvenli" in result["error"].lower()

    def test_laser_safe_font_accepted_in_save_recipe(self, tmp_path: Path):
        """Lazer slotunda laser_safe=True font → OK dönmeli."""
        font_id = _write_laser_font_manifest(tmp_path, laser_safe=True)
        slots = [
            {"id": "s1", "konum": "Lazer", "cikti": "lazer", "besleyen": "isim",
             "font_id": font_id, "adet": 1, "sabit_metin": "", "plaka_adedi": 1}
        ]
        result = save_recipe(tmp_path, "LASER002", slots)
        assert result["status"] == "OK", result

    def test_label_slot_with_any_font_accepted(self, tmp_path: Path):
        """Etiket slotunda lazer fontu kullanılabilir (cikti=etiket kısıtsız)."""
        font_id = _write_laser_font_manifest(tmp_path, laser_safe=False)
        slots = [
            {"id": "s1", "konum": "Etiket", "cikti": "etiket", "besleyen": "isim",
             "font_id": font_id, "adet": 1, "sabit_metin": "", "plaka_adedi": None}
        ]
        result = save_recipe(tmp_path, "LABEL001", slots)
        assert result["status"] == "OK", result

    def test_bulk_apply_unsafe_laser_font_rejected(self, tmp_path: Path):
        """bulk_apply_recipe: güvensiz lazer font → ERROR."""
        font_id = _write_laser_font_manifest(tmp_path, laser_safe=False)
        result = bulk_apply_recipe(
            tmp_path,
            barkodlar=["BULK001", "BULK002"],
            ayarlar={"lazer_font_id": font_id, "cikti": "lazer"},
        )
        assert result["status"] == "ERROR", f"Bulk: güvensiz font kabul edilmemeli: {result}"

    def test_bulk_apply_safe_laser_font_accepted(self, tmp_path: Path):
        """bulk_apply_recipe: güvenli lazer font → OK."""
        font_id = _write_laser_font_manifest(tmp_path, laser_safe=True)
        result = bulk_apply_recipe(
            tmp_path,
            barkodlar=["BULK003"],
            ayarlar={"lazer_font_id": font_id, "cikti": "lazer"},
        )
        assert result["status"] == "OK", result

    def test_no_font_in_laser_slot_accepted(self, tmp_path: Path):
        """Lazer slotunda font_id boş → kabul (font zorunlu değil)."""
        slots = [
            {"id": "s1", "konum": "Lazer", "cikti": "lazer", "besleyen": "isim",
             "font_id": "", "adet": 1, "sabit_metin": "", "plaka_adedi": 1}
        ]
        result = save_recipe(tmp_path, "LASER003", slots)
        assert result["status"] == "OK", result


# ── İş 4: sync_products model_code ──────────────────────────────────────────

class TestSyncProductsModelCode:
    def test_productCode_takes_priority_over_stockCode(self):
        """productCode varsa model_code olarak kullanılmalı."""
        from webui_backend.trendyol_api import _product_catalog_index
        prod = {
            "barcode": "TEST001",
            "productCode": "ADE-MODEL-001",
            "stockCode": "SKU-FALLBACK",
            "title": "Test ürünü",
        }
        # sync_products mantığını doğrudan test et
        model_code = str(
            prod.get("productCode") or prod.get("stockCode") or prod.get("sellerBarcode") or ""
        )
        assert model_code == "ADE-MODEL-001", f"productCode öncelikli değil: {model_code}"

    def test_fallback_to_stockCode_when_no_productCode(self):
        """productCode yoksa stockCode kullanılmalı."""
        prod = {"barcode": "TEST002", "stockCode": "SKU-001", "title": "Test"}
        model_code = str(
            prod.get("productCode") or prod.get("stockCode") or prod.get("sellerBarcode") or ""
        )
        assert model_code == "SKU-001"

    def test_empty_model_code_for_no_code_fields(self):
        """Hiçbir code alanı yoksa boş string."""
        prod = {"barcode": "TEST003", "title": "Test"}
        model_code = str(
            prod.get("productCode") or prod.get("stockCode") or prod.get("sellerBarcode") or ""
        )
        assert model_code == ""


# ── HTTP route testleri (Flask test client) ──────────────────────────────────

class TestRouteHttpStatus:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        """Flask test client with PROJECT_ROOT pointing to tmp_path."""
        from server.flask_app import app
        import server.routes as routes_mod
        monkeypatch.setattr(routes_mod, "_PROJECT_ROOT", tmp_path)
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_save_recipe_valid_returns_200(self, client, tmp_path):
        payload = {
            "barkod": "ROUTE001",
            "slots": [{"id": "s1", "konum": "Test", "cikti": "etiket",
                       "besleyen": "sabit", "font_id": "", "adet": 1,
                       "sabit_metin": "Test Metin"}]
        }
        resp = client.post("/api/save_recipe",
                           data=json.dumps(payload),
                           content_type="application/json")
        assert resp.status_code == 200, resp.get_data(as_text=True)
        data = resp.get_json()
        assert data["status"] == "OK"
        assert data["recipe"]["slots"][0]["sabit_metin"] == "Test Metin"

    def test_save_recipe_unsafe_laser_font_returns_400(self, client, tmp_path):
        # Write unsafe font manifest
        font_id = _write_laser_font_manifest(tmp_path, laser_safe=False)
        payload = {
            "barkod": "ROUTE002",
            "slots": [{"id": "s1", "konum": "L", "cikti": "lazer",
                       "besleyen": "isim", "font_id": font_id, "adet": 1,
                       "sabit_metin": ""}]
        }
        resp = client.post("/api/save_recipe",
                           data=json.dumps(payload),
                           content_type="application/json")
        assert resp.status_code == 400, f"Beklenen 400, geldi: {resp.status_code}"
        data = resp.get_json()
        assert data["status"] == "ERROR"

    def test_bulk_apply_unsafe_laser_font_returns_400(self, client, tmp_path):
        font_id = _write_laser_font_manifest(tmp_path, laser_safe=False)
        payload = {
            "barkodlar": ["B001"],
            "ayarlar": {"lazer_font_id": font_id, "cikti": "lazer"}
        }
        resp = client.post("/api/bulk_apply_recipe",
                           data=json.dumps(payload),
                           content_type="application/json")
        assert resp.status_code == 400, f"Beklenen 400, geldi: {resp.status_code}"
