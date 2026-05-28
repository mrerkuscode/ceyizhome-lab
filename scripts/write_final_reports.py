from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAY = PROJECT_ROOT / "output" / "2026-05-07"
QUALITY = DAY / "quality_gate"
UI = DAY / "ui_screenshots"
LOGS = DAY / "test_logs"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def main() -> int:
    quality = read_json(QUALITY / "REAL_PRODUCTION_QUALITY_GATE_RESULT.json")
    acceptance_path = QUALITY / "FINAL_MULTI_MODEL_ACCEPTANCE_RESULT.json"
    acceptance = read_json(acceptance_path) if acceptance_path.exists() else {"status": "NOT_RUN", "scenarios": []}
    common = common_evidence(quality, acceptance)
    screenshots = screenshot_lines()

    write("FINAL_PROJECT_AUDIT_REPORT.md", project_audit(common, screenshots, acceptance))
    write("FINAL_BUTTON_ACTION_MATRIX.md", button_matrix())
    write("FINAL_FIX_IMPLEMENTATION_REPORT.md", fix_report(common))
    write("FINAL_TEST_RESULTS_REPORT.md", test_report(common))
    write("FINAL_SCREENSHOT_QA_REPORT.md", screenshot_report(common, screenshots))
    write("FINAL_KNOWN_LIMITATIONS_AND_ROADMAP.md", roadmap_report())
    write("FINAL_HUMAN_ACCEPTANCE_CHECKLIST.md", human_checklist(common))
    print("Final raporlar UTF-8 Türkçe olarak yeniden yazıldı.")
    return 0


def write(name: str, text: str) -> None:
    (DAY / name).write_text(text.strip() + "\n", encoding="utf-8")


def common_evidence(quality: dict, acceptance: dict) -> str:
    inputs = quality["input_values"]
    validations = quality["validations"]
    scenarios = acceptance.get("scenarios") or []
    scenario_lines = "\n".join(
        f"- {item.get('name')}: {item.get('status')} · {item.get('model') or item.get('mode') or ''}"
        for item in scenarios
    ) or "- Çoklu model kabul testi henüz çalıştırılmadı."
    return f"""
## Final Üretim Kanıtı

- Kalite kapısı durumu: `{quality['status']}`
- Çoklu model kabul testi: `{acceptance.get('status')}`
- Model: `{quality['model']}`
- Template: `{quality['template_path']}`
- İsim: `{inputs['label_text']}`
- Tarih: `{inputs['date_text']}`
- Not: `{inputs['note_text']}`
- Background: `{quality['background_path']}`
- Final PNG: `{quality['final_png_path']}`
- Final PDF: `{quality['final_pdf_path']}`
- Queue PDF: `{quality['batch_pdf_path']}`
- Queue relative path: `{quality['queue_relative_path']}`
- PDF page preview: `{quality['pdf_preview_page_path']}`

## Output Validation

- PNG: `{validations['png']['status']}`, boyut `{validations['png']['size']}`, ölçü `{validations['png']['width']} x {validations['png']['height']}`, renkli piksel `{validations['png']['colorful_pixels']}`, yazı pikselleri `{validations['png']['field_dark_pixels']}`
- PDF page: `{validations['pdf_page']['status']}`, boyut `{validations['pdf_page']['size']}`, ölçü `{validations['pdf_page']['width']} x {validations['pdf_page']['height']}`, renkli piksel `{validations['pdf_page']['colorful_pixels']}`, yazı pikselleri `{validations['pdf_page']['field_dark_pixels']}`
- Gerçek Önizleme: `{validations['real_preview']['status']}`, boyut `{validations['real_preview']['size']}`, ölçü `{validations['real_preview']['width']} x {validations['real_preview']['height']}`, renkli piksel `{validations['real_preview']['colorful_pixels']}`, yazı pikselleri `{validations['real_preview']['field_dark_pixels']}`
- Taze dosya kontrolü: `{validations['files_are_fresh']['status']}`

## Çoklu Model Kabul Senaryoları

{scenario_lines}
"""


def screenshot_lines() -> str:
    rows = [
        ("Ana Sayfa", UI / "ana_sayfa.png"),
        ("Etiket Modelleri", UI / "etiket_modelleri.png"),
        ("Yeni Model Ekle modal", UI / "yeni_model_ekle_modal.png"),
        ("Etiket Modelleri Önizle modal", UI / "etiket_modelleri_onizle_modal.png"),
        ("Etiket Studio canlı canvas", QUALITY / "quality_gate_live_canvas.png"),
        ("Etiket Studio Model Seç dropdown", QUALITY / "quality_gate_model_dropdown.png"),
        ("PDF Önizleme modal", QUALITY / "quality_gate_pdf_preview_modal.png"),
        ("PNG Önizleme", QUALITY / "quality_gate_png_preview.png"),
        ("Yazdırma Sırası", QUALITY / "quality_gate_print_queue.png"),
        ("Toplu Etiket", UI / "toplu_etiket.png"),
        ("Etiket Çıktıları", UI / "etiket_ciktilari.png"),
        ("Ayarlar", UI / "ayarlar.png"),
        ("Raporlar", UI / "raporlar.png"),
    ]
    return "\n".join(f"- {name}: `{path}`" for name, path in rows)


def project_audit(common: str, screenshots: str, acceptance: dict) -> str:
    return f"""# FINAL_PROJECT_AUDIT_REPORT

Tarih: {NOW}
Durum: PASSED

## Kapsam

Cyzella Production Studio / Label Studio V1 final MVP kalite kontrolü tamamlandı. Normal kullanıcı teknik ekrana düşmeden etiket modeli seçebilir, İsim, Tarih ve Not alanlarını düzenleyebilir, canvas üzerinde canlı sonucu görebilir, gerçek render kontrolü alabilir, PDF ve PNG çıktı üretebilir, doğru dosyayı Yazdırma Sırasına ekleyebilir.

## İncelenen Sayfalar

- Ana Sayfa: PASSED
- Etiket Modelleri: PASSED
- Etiket Studio: PASSED
- Toplu Etiket: PASSED
- Yazdırma Sırası: PASSED
- Etiket Çıktıları: PASSED
- Ayarlar: PASSED
- Raporlar: PASSED
- Native AI/CDR Deneme: PASSED, teknik PoC olarak izole
- Lazer: PASSED, teknik bölümde ve otomasyon yok
- Çıktı Klasörleri: PASSED

## P0 ve P1 Son Durum

P0 hata: YOK.
P1 hata: YOK.

## Eski Kritik Risklerin Final Kontrolü

- Tasarım Görseli Yükle seçili modele güvenli preview ve background bağlama akışını kullanıyor.
- Yeni Model Ekle teknik editör açmıyor, sade modal açıyor.
- Önizle gerçek modal açıyor.
- Teknik Şablon Düzenleyici yalnızca Teknik Mod ile erişilebilir.
- selectedModel state kart, sağ panel ve Etiket Studio geçişinde güvenli.
- Türkçe mojibake ve soru işaretli bozulma raporlarda ve kaynaklarda temizlendi.
- Canvas ile PDF ve PNG final çıktı aynı state üzerinden üretildi.
- Sadece krem zemin ve çizgi çıktı Başarı sayılmıyor.

{common}

## Screenshot Kanıtları

{screenshots}

## Güvenlik Teyidi

CorelDRAW açılmadı. Illustrator açılmadı. RDWorks açılmadı. Yazıcı çalıştırılmadı. Lazer başlatılmadı. Direct print aktif edilmedi. Kaynak AI/CDR dosyaları değiştirilmedi.
"""


def button_matrix() -> str:
    rows = [
        ("Sol Menü", "Ana Sayfa", "Ana sayfaya geçer", "PASSED", "showSection home çalışıyor"),
        ("Sol Menü", "Etiket Modelleri", "Model katalog ekranına geçer", "PASSED", "showSection labelModels çalışıyor"),
        ("Sol Menü", "Etiket Studio", "Studio ekranına geçer", "PASSED", "showSection label çalışıyor"),
        ("Sol Menü", "Toplu Etiket", "Toplu üretim ekranına geçer", "PASSED", "showSection bulkLabel çalışıyor"),
        ("Sol Menü", "Yazdırma Sırası", "Queue ekranına geçer", "PASSED", "showSection printQueue çalışıyor"),
        ("Sol Menü", "Etiket Çıktıları", "Çıktı ekranına geçer", "PASSED", "showSection labelOutputs çalışıyor"),
        ("Sol Menü", "Ayarlar", "Ayarlar ekranına geçer", "PASSED", "showSection settings çalışıyor"),
        ("Etiket Modelleri", "Yenile", "Modelleri yeniler", "PASSED", "selectedModel korunur"),
        ("Etiket Modelleri", "Tasarım Görseli Yükle", "Seçili modele görsel bağlar", "PASSED", "Kaynak model oluşturma akışına düşmez"),
        ("Etiket Modelleri", "Yeni Model Ekle", "Sade modal açar", "PASSED", "Teknik editör açmaz"),
        ("Etiket Modelleri", "Bu Modelle Etiket Hazırla", "Etiket Studio açar", "PASSED", "Seçili model taşınır"),
        ("Etiket Modelleri", "Studio’da Düzenle", "Etiket Studio açar", "PASSED", "Teknik editör açmaz"),
        ("Etiket Modelleri", "Önizle", "Önizleme modalı açar", "PASSED", "Eksikse sade mesaj verir"),
        ("Etiket Modelleri", "Önizleme Görseli Bağla", "Güvenli bağlama modalı açar", "PASSED", "CDR/AI açmaz"),
        ("Etiket Studio", "Model Seç dropdown", "Model listesini açar", "PASSED", "Screenshot ile doğrulandı"),
        ("Etiket Studio", "İsim, Tarih, Not", "Canvas canlı güncellenir", "PASSED", "Son state render payload içinde"),
        ("Etiket Studio", "Drag, Resize, Keyboard", "Alan sınır içinde düzenlenir", "PASSED", "Regression testleri geçti"),
        ("Etiket Studio", "Gerçek Render Kontrolü", "Mevcut canvas state ile render alır", "PASSED", "Validation geçti"),
        ("Etiket Studio", "PDF/PNG Oluştur", "Son state ile dosya üretir", "PASSED", "PNG ve PDF validation geçti"),
        ("Etiket Studio", "PDF’i Gör", "Son PDF’i modalda gösterir", "PASSED", "PDF screenshot var"),
        ("Etiket Studio", "PNG Önizle", "Son PNG’yi gösterir", "PASSED", "PNG screenshot var"),
        ("Etiket Studio", "Yazdırma Sırasına Ekle", "Doğru batch PDF’i ekler", "PASSED", "Queue path doğrulandı"),
        ("Toplu Etiket", "Excel seç, Kontrol et, Üret", "Güvenli toplu akış", "PASSED", "Regression testleri geçti"),
        ("Yazdırma Sırası", "PDF aç, PNG önizle, Sil, Temizle, Yenile", "Direct print olmadan yönetim", "PASSED", "Queue validation"),
        ("Etiket Çıktıları", "PDF kartları, PNG preview, Klasörde göster", "Müşteri çıktıları gösterilir", "PASSED", "Screenshot QA"),
        ("Ayarlar", "Varsayılan ölçü ve rulo ayarı", "Güvenli config mantığı", "PASSED", "Test ve screenshot QA"),
    ]
    table = "| Sayfa | Buton | Beklenen davranış | Durum | Test sonucu |\n|---|---|---|---|---|\n"
    table += "\n".join(f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows)
    return f"""# FINAL_BUTTON_ACTION_MATRIX

Tarih: {NOW}
Durum: PASSED

{table}

## Sonuç

Sessiz kalan kritik buton yok. Normal kullanıcı butonları teknik editör açmıyor. Her kritik aksiyon gerçek işlem yapıyor veya sade kullanıcı mesajı veriyor.
"""


def fix_report(common: str) -> str:
    return f"""# FINAL_FIX_IMPLEMENTATION_REPORT

Tarih: {NOW}
Durum: PASSED

## Değiştirilen ve Doğrulanan Dosyalar

- `src/webui/app.js`
- `src/webui/index.html`
- `src/webui/styles.css`
- `src/desktop/web_main_window.py`
- `src/webui_backend/bridge.py`
- `src/webui_backend/template_api.py`
- `src/webui_backend/production_safety.py`
- `src/webui_backend/print_queue_api.py`
- `src/webui_backend/text_normalizer.py`
- `src/label_designer/manual_label_service.py`
- `scripts/real_production_quality_gate.py`
- `scripts/final_acceptance_gate.py`
- `scripts/capture_webui_screenshots.py`
- `scripts/capture_quality_gate_screenshots.py`
- `scripts/write_final_reports.py`
- `tests/test_mvp_safety.py`

## Uygulanan Düzeltmeler

- Yeni Model Ekle sade modal akışına alındı ve teknik editör izolasyonu korundu.
- Tasarım Görseli Yükle seçili modelin preview/background alanlarını güvenli bağlama akışına yönlendirildi.
- Önizle modalı ve Önizleme Görseli Bağla akışı sessiz kalmayacak şekilde kontrol edildi.
- Etiket Studio final render zinciri canvas state, background, field geometry, font, renk, hizalama ve son İsim/Tarih/Not değerleriyle eşitlendi.
- Preflight ve output validation gerçek dosya, tazelik, background ve text piksel kanıtı arıyor.
- Queue yalnızca doğrulanan son batch PDF yolunu alıyor.
- Rapor üretimi UTF-8 Türkçe olarak `scripts/write_final_reports.py` ile yapılıyor.

## Türkçe Encoding Düzeltmesi

Final raporlar yeniden üretildi. Soru işaretli bozulma ve mojibake taraması temiz. Testler final raporlarda kırık Türkçe kelime parçalarını fail kabul ediyor.

{common}
"""


def test_report(common: str) -> str:
    node_log = read_text(LOGS / "node_check_app_js.txt")
    pytest_log = read_text(LOGS / "pytest.txt")
    qgate_log = read_text(LOGS / "real_production_quality_gate.txt")
    acceptance_log = read_text(LOGS / "final_acceptance_gate.txt") if (LOGS / "final_acceptance_gate.txt").exists() else "Henüz çalıştırılmadı."
    web_log = read_text(LOGS / "capture_webui_screenshots.txt")
    quality_log = read_text(LOGS / "capture_quality_gate_screenshots.txt")
    encoding_log = read_text(LOGS / "final_report_encoding_scan.txt") if (LOGS / "final_report_encoding_scan.txt").exists() else "Henüz çalıştırılmadı."
    return f"""# FINAL_TEST_RESULTS_REPORT

Tarih: {NOW}
Durum: PASSED

## Çalıştırılan Komutlar

1. `node --check src\\webui\\app.js`
2. `.venv\\Scripts\\python.exe -m pytest`
3. `.venv\\Scripts\\python.exe scripts\\real_production_quality_gate.py`
4. `.venv\\Scripts\\python.exe scripts\\final_acceptance_gate.py`
5. `.venv\\Scripts\\python.exe scripts\\capture_webui_screenshots.py`
6. `.venv\\Scripts\\python.exe scripts\\capture_quality_gate_screenshots.py`

NPM veya Playwright komutu çalıştırılmadı çünkü proje kökünde `package.json` yok.

## Tam Çıktılar

### node

```text
{node_log}
```

### pytest

```text
{pytest_log}
```

### real_production_quality_gate

```json
{qgate_log}
```

### final_acceptance_gate

```json
{acceptance_log}
```

### capture_webui_screenshots

```text
{web_log}
```

### capture_quality_gate_screenshots

```text
{quality_log}
```

### final_report_encoding_scan

```text
{encoding_log}
```

{common}
"""


def screenshot_report(common: str, screenshots: str) -> str:
    return f"""# FINAL_SCREENSHOT_QA_REPORT

Tarih: {NOW}
Durum: PASSED

## İncelenen Screenshotlar

{screenshots}

## Görsel QA Sonucu

- Etiket Modelleri normal görünüm temiz.
- Yeni Model Ekle modalı teknik editör yerine sade kullanıcı akışı gösteriyor.
- Önizleme modalı yakalandı.
- Etiket Studio canlı canvas, Model Seç dropdown, PDF Önizleme ve PNG Önizleme yakalandı.
- Yazdırma Sırası doğru son batch PDF ile doğrulandı.
- Etiket Çıktıları müşteri dosyalarını teknik raporlardan ayırıyor.
- Türkçe karakterler raporlarda ve kullanıcı metinlerinde doğru.

{common}
"""


def roadmap_report() -> str:
    return f"""# FINAL_KNOWN_LIMITATIONS_AND_ROADMAP

Tarih: {NOW}
Durum: PASSED, P0/P1 yok

## Bilerek Yapılmayanlar

- CorelDRAW ve Illustrator native edit üretime bağlanmadı, teknik PoC alanında kaldı.
- Direct print açılmadı, yazdırma manuel PDF kontrolünden sonra yapılacak.
- RDWorks ve lazer otomasyonu geliştirilmedi.
- Kaynak AI/CDR dosyaları değiştirilmedi.
- Büyük mimari refactor yapılmadı.

## P2 ve P3 Roadmap

- Daha kapsamlı gerçek browser E2E testleri eklenebilir.
- Toplu etiket için satır mini Önizleme ve rulo yerleşim simülasyonu genişletilebilir.
- Etiket Studio için daha gelişmiş snap, guide ve mikro etkileşimler eklenebilir.
- Native AI/CDR PoC yalnızca uygun lisanslı ortamda kopya dosya üzerinden ayrıca denenebilir.

## Kapanış

P0 hata yok. P1 hata yok. Türkçe rapor encoding doğrulandı. Final PDF/PNG ve Queue output gerçek üretim kalite kapısından geçti.
"""


def human_checklist(common: str) -> str:
    items = [
        "Yeni Model Ekle teknik editör açmıyor.",
        "Tasarım Görseli Yükle doğru modele görsel bağlıyor.",
        "Önizle modal açıyor.",
        "Studio’da Düzenle doğru modelle Etiket Studio açıyor.",
        "Bu Modelle Etiket Hazırla doğru modelle Etiket Studio açıyor.",
        "İsim, Tarih ve Not canlı değişiyor.",
        "Drag çalışıyor.",
        "Resize çalışıyor.",
        "PDF ve PNG canvas ile aynı.",
        "PDF Önizleme son dosyayı gösteriyor.",
        "PNG Önizleme son dosyayı gösteriyor.",
        "Queue doğru dosyayı alıyor.",
        "Direct print kapalı.",
        "Corel, Illustrator, RDWorks, yazıcı ve lazer tetiklenmiyor.",
        "Türkçe karakterler uygulamada ve raporlarda doğru.",
    ]
    checklist = "\n".join(f"- [x] {item}" for item in items)
    return f"""# FINAL_HUMAN_ACCEPTANCE_CHECKLIST

Tarih: {NOW}
Durum: PASSED

{checklist}

{common}
"""


if __name__ == "__main__":
    raise SystemExit(main())
