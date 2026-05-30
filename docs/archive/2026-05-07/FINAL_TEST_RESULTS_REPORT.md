# FINAL_TEST_RESULTS_REPORT

Tarih: 2026-05-07 08:31:00
Durum: PASSED

## Çalıştırılan Komutlar

1. `node --check src\webui\app.js`
2. `.venv\Scripts\python.exe -m pytest`
3. `.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
4. `.venv\Scripts\python.exe scripts\final_acceptance_gate.py`
5. `.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`
6. `.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`

NPM veya Playwright komutu çalıştırılmadı çünkü proje kökünde `package.json` yok.

## Tam Çıktılar

### node

```text
node --check passed (no syntax errors).
```

### pytest

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\Pc\Documents\New project\production-bot
configfile: pytest.ini
testpaths: tests
collected 101 items

tests\test_mvp_safety.py ............................................... [ 46%]
......................................................                   [100%]

============================= 101 passed in 1.97s =============================
```

### real_production_quality_gate

```json
{
  "status": "PASSED",
  "model": "01 A Gold Rulo Etiket",
  "template_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\01_a_gold.json",
  "input_values": {
    "label_text": "Ayşe & Mehmet QA",
    "date_text": "15.05.26",
    "note_text": "Nişan hatırası"
  },
  "background_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\assets\\label_backgrounds\\normalized\\01_a_gold_preview_50x30.png",
  "live_canvas_screenshot": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\ui_screenshots\\manuel_etiket.png",
  "render_preview_png_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\preview\\manual_label\\manual_preview_01_a_gold_Ayse_Mehmet_QA.png",
  "final_png_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_9.png",
  "final_pdf_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_9.pdf",
  "batch_pdf_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_9.pdf",
  "pdf_preview_page_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\quality_gate\\quality_gate_pdf_page.png",
  "queue_relative_path": "output/2026-05-07/print/manual/2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_9.pdf",
  "queue_result": {
    "status": "ADDED",
    "message": "Etiket işi yazdırma sırasına eklendi.",
    "id": "1d0eac3dc2e44fd6b5ed63a7ea525a1e"
  },
  "pdf_preview_payload": {
    "status": "OK",
    "page_count": 1,
    "preview_pages": [
      {
        "page": 1,
        "preview_png_path": "output/2026-05-07/preview/pdf/2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_9/page_001.png",
        "preview_url": "file:///C:/Users/Pc/Documents/New%20project/production-bot/output/2026-05-07/preview/pdf/2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_9/page_001.png"
      }
    ]
  },
  "validations": {
    "png": {
      "status": "PASSED",
      "reason": "",
      "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_9.png",
      "size": 138866,
      "width": 591,
      "height": 354,
      "colorful_pixels": 678,
      "dark_pixels": 126,
      "field_dark_pixels": {
        "label_text": 57,
        "date_text": 15,
        "note_text": 63
      }
    },
    "pdf_page": {
      "status": "PASSED",
      "reason": "",
      "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\quality_gate\\quality_gate_pdf_page.png",
      "size": 302158,
      "width": 900,
      "height": 539,
      "colorful_pixels": 582,
      "dark_pixels": 72,
      "field_dark_pixels": {
        "label_text": 37,
        "date_text": 7,
        "note_text": 52
      }
    },
    "real_preview": {
      "status": "PASSED",
      "reason": "",
      "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\preview\\manual_label\\manual_preview_01_a_gold_Ayse_Mehmet_QA.png",
      "size": 138866,
      "width": 591,
      "height": 354,
      "colorful_pixels": 678,
      "dark_pixels": 126,
      "field_dark_pixels": {
        "label_text": 57,
        "date_text": 15,
        "note_text": 63
      }
    },
    "files_are_fresh": {
      "status": "PASSED",
      "started_at": 1778131655.957763
    }
  }
}
```

### final_acceptance_gate

```json
{
  "status": "PASSED",
  "created_at": "2026-05-07 08:27:45",
  "scenarios": [
    {
      "name": "A - Hazır model",
      "status": "PASSED",
      "template_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\01_a_gold.json",
      "model": "01 A Gold Rulo Etiket",
      "input_values": {
        "label_text": "Ayşe & Mehmet QA",
        "date_text": "15.05.26",
        "note_text": "Nişan hatırası"
      },
      "background_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\assets\\label_backgrounds\\normalized\\01_a_gold_preview_50x30.png",
      "preview_png_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\preview\\manual_label\\manual_preview_01_a_gold_Ayse_Mehmet_QA.png",
      "final_png_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_10.png",
      "final_pdf_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_10.pdf",
      "batch_pdf_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_10.pdf",
      "queue_relative_path": "output/2026-05-07/print/manual/2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_10.pdf",
      "queue_result": {
        "status": "ADDED",
        "message": "Etiket işi yazdırma sırasına eklendi.",
        "id": "ad19f2bde15747759682d134466a9726"
      },
      "pdf_preview_page_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\quality_gate\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_10_pdf_page.png",
      "validations": {
        "png": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_10.png",
          "size": 138866,
          "width": 591,
          "height": 354,
          "colorful_pixels": 678,
          "dark_pixels": 126,
          "field_dark_pixels": {
            "label_text": 57,
            "date_text": 15,
            "note_text": 63
          }
        },
        "pdf_page": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\quality_gate\\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_10_pdf_page.png",
          "size": 302158,
          "width": 900,
          "height": 539,
          "colorful_pixels": 582,
          "dark_pixels": 72,
          "field_dark_pixels": {
            "label_text": 37,
            "date_text": 7,
            "note_text": 52
          }
        },
        "real_preview": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\preview\\manual_label\\manual_preview_01_a_gold_Ayse_Mehmet_QA.png",
          "size": 138866,
          "width": 591,
          "height": 354,
          "colorful_pixels": 678,
          "dark_pixels": 126,
          "field_dark_pixels": {
            "label_text": 57,
            "date_text": 15,
            "note_text": 63
          }
        },
        "files_are_fresh": {
          "status": "PASSED",
          "started_at": 1778131664.170379
        }
      },
      "technical_editor_opened": false
    },
    {
      "name": "B - İkinci mevcut model",
      "status": "PASSED",
      "template_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\03_a_gold.json",
      "model": "yesıl",
      "input_values": {
        "label_text": "Ayşe & Mehmet QA",
        "date_text": "15.05.26",
        "note_text": "Nişan hatırası"
      },
      "background_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\assets\\label_backgrounds\\03_a_gold_preview.jpg",
      "preview_png_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\preview\\manual_label\\manual_preview_03_a_gold_Ayse_Mehmet_QA.png",
      "final_png_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_yesil_Ayse-Mehmet-QA_40x40_1adet_2.png",
      "final_pdf_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_yesil_Ayse-Mehmet-QA_40x40_1adet_2.pdf",
      "batch_pdf_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_yesil_Ayse-Mehmet-QA_40x40_1adet_batch_2.pdf",
      "queue_relative_path": "output/2026-05-07/print/manual/2026-05-07_yesil_Ayse-Mehmet-QA_40x40_1adet_batch_2.pdf",
      "queue_result": {
        "status": "ADDED",
        "message": "Etiket işi yazdırma sırasına eklendi.",
        "id": "4a1ef1fe98f14e86a93319336bfd48ca"
      },
      "pdf_preview_page_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\quality_gate\\2026-05-07_yesil_Ayse-Mehmet-QA_40x40_1adet_batch_2_pdf_page.png",
      "validations": {
        "png": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_yesil_Ayse-Mehmet-QA_40x40_1adet_2.png",
          "size": 80895,
          "width": 472,
          "height": 472,
          "colorful_pixels": 113,
          "dark_pixels": 98,
          "field_dark_pixels": {
            "label_text": 77,
            "date_text": 15,
            "note_text": 16
          }
        },
        "pdf_page": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\quality_gate\\2026-05-07_yesil_Ayse-Mehmet-QA_40x40_1adet_batch_2_pdf_page.png",
          "size": 261533,
          "width": 900,
          "height": 900,
          "colorful_pixels": 113,
          "dark_pixels": 78,
          "field_dark_pixels": {
            "label_text": 83,
            "date_text": 15,
            "note_text": 10
          }
        },
        "real_preview": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\preview\\manual_label\\manual_preview_03_a_gold_Ayse_Mehmet_QA.png",
          "size": 80895,
          "width": 472,
          "height": 472,
          "colorful_pixels": 113,
          "dark_pixels": 98,
          "field_dark_pixels": {
            "label_text": 77,
            "date_text": 15,
            "note_text": 16
          }
        },
        "files_are_fresh": {
          "status": "PASSED",
          "started_at": 1778131664.507416
        }
      },
      "technical_editor_opened": false
    },
    {
      "name": "C - Yeni model",
      "status": "PASSED",
      "template_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\04_a_qa.json",
      "model": "Final QA Kabul Modeli",
      "input_values": {
        "label_text": "Ayşe & Mehmet QA",
        "date_text": "15.05.26",
        "note_text": "Nişan hatırası"
      },
      "background_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\assets\\label_backgrounds\\04_a_qa_preview.png",
      "preview_png_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\preview\\manual_label\\manual_preview_04_a_qa_Ayse_Mehmet_QA.png",
      "final_png_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_2.png",
      "final_pdf_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_2.pdf",
      "batch_pdf_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_batch_2.pdf",
      "queue_relative_path": "output/2026-05-07/print/manual/2026-05-07_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_batch_2.pdf",
      "queue_result": {
        "status": "ADDED",
        "message": "Etiket işi yazdırma sırasına eklendi.",
        "id": "d33c264f08194d17aa384a394483c641"
      },
      "pdf_preview_page_path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\quality_gate\\2026-05-07_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_batch_2_pdf_page.png",
      "validations": {
        "png": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\print\\manual\\2026-05-07_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_2.png",
          "size": 138807,
          "width": 591,
          "height": 354,
          "colorful_pixels": 678,
          "dark_pixels": 112,
          "field_dark_pixels": {
            "label_text": 46,
            "date_text": 11,
            "note_text": 42
          }
        },
        "pdf_page": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\quality_gate\\2026-05-07_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_batch_2_pdf_page.png",
          "size": 301755,
          "width": 900,
          "height": 539,
          "colorful_pixels": 582,
          "dark_pixels": 73,
          "field_dark_pixels": {
            "label_text": 35,
            "date_text": 12,
            "note_text": 39
          }
        },
        "real_preview": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-07\\preview\\manual_label\\manual_preview_04_a_qa_Ayse_Mehmet_QA.png",
          "size": 138807,
          "width": 591,
          "height": 354,
          "colorful_pixels": 678,
          "dark_pixels": 112,
          "field_dark_pixels": {
            "label_text": 46,
            "date_text": 11,
            "note_text": 42
          }
        },
        "files_are_fresh": {
          "status": "PASSED",
          "started_at": 1778131664.780268
        }
      },
      "technical_editor_opened": false
    }
  ],
  "security": {
    "coreldraw_opened": false,
    "illustrator_opened": false,
    "rdworks_opened": false,
    "printer_started": false,
    "laser_started": false,
    "direct_print_enabled": false,
    "source_ai_cdr_modified": false
  }
}
```

### capture_webui_screenshots

```text
capture_webui_screenshots.py passed.
```

### capture_quality_gate_screenshots

```text
capture_quality_gate_screenshots.py passed.
```

### final_report_encoding_scan

```text
FINAL_PROJECT_AUDIT_REPORT.md: bad=none; has_clean_turkish=True
FINAL_BUTTON_ACTION_MATRIX.md: bad=none; has_clean_turkish=True
FINAL_FIX_IMPLEMENTATION_REPORT.md: bad=none; has_clean_turkish=True
FINAL_TEST_RESULTS_REPORT.md: bad=none; has_clean_turkish=True
FINAL_SCREENSHOT_QA_REPORT.md: bad=none; has_clean_turkish=True
FINAL_KNOWN_LIMITATIONS_AND_ROADMAP.md: bad=none; has_clean_turkish=True
FINAL_HUMAN_ACCEPTANCE_CHECKLIST.md: bad=none; has_clean_turkish=True
PROBLEMS=none
```


## Final Üretim Kanıtı

- Kalite kapısı durumu: `PASSED`
- Çoklu model kabul testi: `PASSED`
- Model: `01 A Gold Rulo Etiket`
- Template: `C:\Users\Pc\Documents\New project\production-bot\templates\designs\01_a_gold.json`
- İsim: `Ayşe & Mehmet QA`
- Tarih: `15.05.26`
- Not: `Nişan hatırası`
- Background: `C:\Users\Pc\Documents\New project\production-bot\assets\label_backgrounds\normalized\01_a_gold_preview_50x30.png`
- Final PNG: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\print\manual\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_9.png`
- Final PDF: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\print\manual\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_9.pdf`
- Queue PDF: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\print\manual\2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_9.pdf`
- Queue relative path: `output/2026-05-07/print/manual/2026-05-07_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_9.pdf`
- PDF page preview: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-07\quality_gate\quality_gate_pdf_page.png`

## Output Validation

- PNG: `PASSED`, boyut `138866`, ölçü `591 x 354`, renkli piksel `678`, yazı pikselleri `{'label_text': 57, 'date_text': 15, 'note_text': 63}`
- PDF page: `PASSED`, boyut `302158`, ölçü `900 x 539`, renkli piksel `582`, yazı pikselleri `{'label_text': 37, 'date_text': 7, 'note_text': 52}`
- Gerçek Önizleme: `PASSED`, boyut `138866`, ölçü `591 x 354`, renkli piksel `678`, yazı pikselleri `{'label_text': 57, 'date_text': 15, 'note_text': 63}`
- Taze dosya kontrolü: `PASSED`

## Çoklu Model Kabul Senaryoları

- A - Hazır model: PASSED · 01 A Gold Rulo Etiket
- B - İkinci mevcut model: PASSED · yesıl
- C - Yeni model: PASSED · Final QA Kabul Modeli
