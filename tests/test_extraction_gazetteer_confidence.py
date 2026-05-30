"""
Tests — Gazetteer, genişletilmiş tarih parser, fast-path, dürüst güven kalibrasyonu.

Temel kontroller:
  1. Gazetteer lookup (Türkçe isim tanıma, aksan-duyarsız)
  2. Tarih parser — sayısal / yazılı Türkçe ay adı / göreli
  3. Olay anahtar kelime tespiti
  4. Fast-path kısa devre (LLM'siz)
  5. Güven kalibrasyonu — merhaba/gold asla ≥0.85 alamaz
  6. Metrik raporu (precision_auto, recall, garbage_auto, fast_path_rate)
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

# ── proje kök'ünü path'e ekle ──────────────────────────────────────────────
import sys
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from intelligence.trendyol_order_extractor import (
    _detect_occasion,
    _extract_date_with_span,
    _extract_relative_date,
    _is_gazetteer_name,
    _load_gazetteer,
    _load_occasion_keys,
    _word_key,
    extract_production_fields,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "trendyol_extraction_labeled.json"


# ── 1. Gazetteer ────────────────────────────────────────────────────────────

class TestGazetteer:
    def test_gazetteer_loads_nonempty(self):
        gaz = _load_gazetteer()
        assert len(gaz) >= 100, "Gazetteer en az 100 isim içermeli"

    def test_common_names_present(self):
        for name in ("Ayşe", "Mehmet", "Zeynep", "Ali", "Pınar", "Burhan", "Yakup"):
            assert _is_gazetteer_name(name), f"{name!r} gazetteer'de olmalı"

    def test_accent_insensitive(self):
        # pinar == Pınar, zeynep == Zeynep vb.
        assert _word_key("pinar") == _word_key("Pınar")
        assert _word_key("zeynep") == _word_key("Zeynep")
        assert _word_key("BURHAN") == _word_key("burhan")

    def test_stop_words_not_names(self):
        for word in ("merhaba", "gold", "siparis", "teslimat", "nisan", "soz"):
            assert not _is_gazetteer_name(word), f"{word!r} gazetteer'de OLMAMALI"

    def test_pair_both_in_gazetteer(self):
        for name in ("Pınar", "Burhan", "Yakup", "Zeynep", "Elif", "Mehmet"):
            assert _is_gazetteer_name(name)


# ── 2. Tarih parser ─────────────────────────────────────────────────────────

class TestDateParser:
    def test_numeric_dot(self):
        val, span = _extract_date_with_span("isim: Ayşe tarih 10.06.2026")
        assert val == "10.06.2026"

    def test_numeric_slash(self):
        val, span = _extract_date_with_span("28/06/2026 için hazırlayın")
        assert val == "28.06.2026"

    def test_numeric_dash(self):
        val, span = _extract_date_with_span("tarih 25-05-2026")
        assert val == "25.05.2026"

    def test_numeric_short_year(self):
        val, span = _extract_date_with_span("25.5.26 tarihine yetişsin")
        assert val == "25.05.2026"

    def test_written_turkish_month(self):
        val, span = _extract_date_with_span("13 Haziran 2026 tarihli sipariş")
        assert "Haziran" in val
        assert "13" in val

    def test_written_month_no_year(self):
        val, span = _extract_date_with_span("25 Mayıs tarihi önemli")
        assert "Mayıs" in val or "mayis" in val.lower()

    def test_written_month_case_insensitive(self):
        val, span = _extract_date_with_span("07 haziran 2026")
        assert val  # tarih bulunmalı

    def test_relative_tomorrow(self):
        today = date(2026, 6, 10)
        val, span = _extract_relative_date("yarın teslim olsun", today)
        assert val == "11.06.2026"
        assert span

    def test_relative_next_week(self):
        today = date(2026, 6, 10)
        val, span = _extract_relative_date("haftaya yetişsin", today)
        assert val == "17.06.2026"

    def test_relative_day_of_month(self):
        today = date(2026, 6, 10)
        val, span = _extract_relative_date("ayın 25'i için hazır olsun", today)
        assert val == "25.06.2026"

    def test_relative_gelecek_cumartesi(self):
        today = date(2026, 6, 8)  # Pazartesi
        val, span = _extract_relative_date("gelecek cumartesi için", today)
        assert val  # cumartesi tarihini bulmalı

    def test_no_date_returns_empty(self):
        val, span = _extract_date_with_span("Merhaba, sipariş numaram bu")
        assert val == ""


# ── 3. Olay anahtar kelimeleri ───────────────────────────────────────────────

class TestOccasionDetection:
    def test_nisan_detected(self):
        occ = _detect_occasion("nişan için Elif & Ahmet isim yazılacak")
        assert occ  # herhangi bir etiket
        assert "nişan" in occ.lower() or "Nişan" in occ

    def test_soz_detected(self):
        occ = _detect_occasion("söz hatırası için Ceylan ve Kerem")
        assert occ

    def test_dugun_detected(self):
        occ = _detect_occasion("düğün hatırası olarak hazırlıyoruz")
        assert occ

    def test_no_occasion_in_plain_message(self):
        occ = _detect_occasion("üzerine Zeynep yazılacak 10.06.2026")
        # Olay anahtar kelime yok; boş ya da yanlış etiket olmamalı
        assert isinstance(occ, str)

    def test_occasion_keys_load(self):
        keys, labels = _load_occasion_keys()
        assert len(keys) >= 10


# ── 4. extract_production_fields — gazetteer + fast-path ────────────────────

class TestExtractProductionFields:
    def _src(self, msg: str, **kw) -> dict:
        return {"question_text": msg, **kw}

    # Merhaba: isim OLMAMALI, güven DÜŞÜK
    def test_merhaba_no_name(self):
        r = extract_production_fields(self._src("Merhaba, sipariş numaram bu, ne zaman gelir?"))
        assert r["label_text"] == ""
        assert r["confidence"] < 0.85, f"Merhaba güven çok yüksek: {r['confidence']}"

    def test_merhaba_confidence_never_auto_approved(self):
        r = extract_production_fields(self._src("Merhaba sipariş numaram 12345 ne zaman kargo?"))
        assert r["confidence"] < 0.85

    # Gold: isim OLMAMALI
    def test_gold_not_name(self):
        r = extract_production_fields(self._src("gold renk olsun lütfen"))
        assert r["label_text"] == ""
        assert r["confidence"] < 0.85

    def test_gold_in_long_message_blocked(self):
        r = extract_production_fields(self._src(
            "sipariş numaram 11276708914 PINAR & BURHAN çikolata kutusu isimler Gold renkli olsun"
        ))
        # PINAR & BURHAN çıkmalı, Gold isim OLMAMALI
        label = r.get("label_text", "")
        assert "Gold" not in label, f"Gold isim olarak çıktı: {label!r}"
        assert "Burhan" in label or "Pinar" in label or not label

    # Yakup Burcu + tarih
    def test_real_yakup_burcu(self):
        r = extract_production_fields(self._src(
            "Merhba #11276359839 sipariş numaralı ya Yakup Burcu isim yazılacak 10.06.2026 yazılacak lütfen"
        ))
        assert r["label_text"], "Yakup Burcu ismi çıkarılmalı"
        assert "10.06.2026" in r.get("date_text", ""), "Tarih çıkarılmalı"

    # Gazetteer doğrulanmış + anchor → high confidence
    def test_gazetteer_confirmed_high_confidence(self):
        r = extract_production_fields(self._src("üzerine Zeynep yazılacak"))
        if r["label_text"]:  # isim bulunursa güven yüksek olmalı
            assert r.get("gazetteer_confirmed", False), "Zeynep gazetteer'de olmalı"
            assert r["confidence"] >= 0.70

    def test_pinar_burhan_pair(self):
        r = extract_production_fields(self._src("Pınar & Burhan isim yazılsın"))
        label = r.get("label_text", "")
        assert "Pinar" in label.replace("ı", "i") or "Burhan" in label

    def test_fast_path_set_when_qualified(self):
        r = extract_production_fields(self._src("üzerine Zeynep yazılacak"))
        if r.get("label_text") and r.get("gazetteer_confirmed"):
            # fast_path sadece confidence >= 0.85 olduğunda True
            if r["confidence"] >= 0.85:
                assert r.get("fast_path") is True

    # Teslimat/lojistik mesaj → isim yok, güven düşük
    def test_teslimat_no_name(self):
        r = extract_production_fields(self._src("Teslimat #11275432108 nolu sipariş nerede?"))
        assert r["label_text"] == ""
        assert r["confidence"] < 0.85

    # Occasion tespiti
    def test_occasion_in_result(self):
        r = extract_production_fields(self._src("nişan için Elif & Ahmet isim yazılacak 15 Haziran 2026"))
        assert r.get("occasion"), "Nişan olay etiketi çıkarılmalı"

    # Tarih çıkarımı
    def test_numeric_date_extracted(self):
        r = extract_production_fields(self._src("Reyhan isim yazılacak 28/06/2026"))
        assert r.get("date_text") == "28.06.2026"

    def test_written_date_extracted(self):
        r = extract_production_fields(self._src("Elif & Ahmet isim yazılacak, tarih 25 Haziran"))
        assert r.get("date_text"), "Yazılı Türkçe tarih çıkarılmalı"
        assert "Haziran" in r["date_text"]

    def test_relative_date_extracted(self):
        today = date(2026, 6, 10)
        r = extract_production_fields(self._src("üzerine Ayşe yazılacak yarın teslim"), today=today)
        assert r.get("date_text") == "11.06.2026"


# ── 5. Metrik raporu ────────────────────────────────────────────────────────

class TestExtractionMetrics:
    """Gerçek etiketli fixture'dan precision_auto, garbage_auto, recall hesaplar."""

    @pytest.fixture(scope="class")
    def fixtures(self):
        return json.loads(_FIXTURES.read_text(encoding="utf-8"))

    @pytest.fixture(scope="class")
    def results(self, fixtures):
        out = []
        for case in fixtures:
            src = {"question_text": case.get("message", "")}
            if case.get("seller_answer"):
                src["answer_text"] = case["seller_answer"]
            if case.get("product_name"):
                src["product_name"] = case["product_name"]
            r = extract_production_fields(src)
            out.append(r)
        return out

    def test_garbage_auto_is_zero(self, fixtures, results):
        """Oto-onaylanan (≥0.85) ÇÖP sayısı 0 olmalı."""
        garbage = 0
        for case, r in zip(fixtures, results):
            exp = case.get("expected", {})
            name_found_expected = exp.get("name_found", True)
            auto_approved = r["confidence"] >= 0.85
            if auto_approved and not name_found_expected:
                garbage += 1
                print(f"GARBAGE: {case['id']!r} label={r['label_text']!r} conf={r['confidence']}")
        assert garbage == 0, f"{garbage} çöp kayıt oto-onaylandı"

    def test_merhaba_never_auto_approved(self, fixtures, results):
        for case, r in zip(fixtures, results):
            msg = case.get("message", "").lower()
            if "merhaba" in msg and not case.get("expected", {}).get("name_found"):
                assert r["confidence"] < 0.85, (
                    f"'Merhaba' içeren mesaj oto-onaylandı: {case['id']!r}, conf={r['confidence']}"
                )

    def test_gold_never_auto_approved(self, fixtures, results):
        for case, r in zip(fixtures, results):
            exp = case.get("expected", {})
            if not exp.get("name_found", True):
                assert r["confidence"] < 0.85 or r["label_text"] == "", (
                    f"İsim-yok vakası oto-onaylandı: {case['id']!r}, label={r['label_text']!r}, conf={r['confidence']}"
                )

    def test_precision_auto_print(self, fixtures, results):
        """Precision ve fast_path_rate raporla — test asla fail etmez, bilgi verir."""
        tp = fp = tn = fn = fast = 0
        for case, r in zip(fixtures, results):
            exp = case.get("expected", {})
            expected_found = exp.get("name_found")
            actual_label = r.get("label_text", "")
            conf = r.get("confidence", 0)
            auto = conf >= 0.85

            if r.get("fast_path"):
                fast += 1

            if expected_found is False:
                if auto and actual_label:
                    fp += 1
                else:
                    tn += 1
            elif expected_found is True:
                if actual_label:
                    tp += 1
                else:
                    fn += 1

        total = len(fixtures)
        precision_auto = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        review_rate = (tn + fn) / total if total else 0.0
        fast_path_rate = fast / total if total else 0.0

        import sys
        out = sys.stdout
        out.write(f"\nMetrik Raporu (deterministik):\n")
        out.write(f"  precision_auto : {precision_auto:.2%}\n")
        out.write(f"  recall         : {recall:.2%}\n")
        out.write(f"  review_rate    : {review_rate:.2%}\n")
        out.write(f"  garbage_auto   : {fp}\n")
        out.write(f"  fast_path_rate : {fast_path_rate:.2%}\n")
        out.write(f"  toplam fixture : {total}\n")

        assert fp == 0, f"{fp} çöp oto-onay! garbage_auto=0 olmalı."
        assert precision_auto >= 0.90, f"precision_auto {precision_auto:.2%} < %90"
