# TEST_COMMAND_REAL_USER_QA_REPORT

Tarih: 2026-05-20 04:09:37
Durum: PASSED

## Okunan Standart Dosyalar

- `START_HERE_FOR_CODEX.md`
- `PROJECT_MASTER_CONTEXT.md`
- `CODEX_LEAD_DEVELOPER_MANUAL.md`
- `REAL_USER_TESTING_STANDARD.md`
- `HUMAN_QA_PROTOCOL.md`
- `INTERACTION_TESTING_GUIDE.md`
- `BUTTON_CLICK_TESTING_STANDARD.md`
- `OUTPUT_VALIDATION_STANDARD.md`
- `VISUAL_SCREENSHOT_QA_GUIDE.md`
- `QA_ACCEPTANCE_CHECKLIST.md`
- `CODEX_CURRENT_PRIORITY.md`
- `TEST_COMMAND_REAL_USER_QA_PROTOCOL.md`

## Test Edilen Sayfalar ve Akışlar

- Ana Sayfa
- Etiket Modelleri
- Etiket Studio
- Toplu Etiket
- Yazdırma Sırası
- Etiket Çıktıları
- Ayarlar

## Test Edilen Kritik Davranışlar

- Etiket Modelleri gerçek click: Yenile, Yeni Model Ekle, Görsel Bağla, Önizle, Etiket Hazırla, Studio’da Düzenle, filtreler, Teknik Mod.
- Etiket Studio gerçek pointer/keyboard interaction: drag, corner resize, side resize, zoom %100/%150/%200, Arrow/Shift+Arrow/Alt+Arrow.
- Output validation: PDF/PNG background, İsim/Tarih/Not, stale dosya kontrolü, queue path doğruluğu.
- Yazdırma güvenliği: Studio ve queue içindeki Yazdır butonları safe modal açar; silent/direct print tetiklenmez.
- Screenshot QA: UI screenshotları ve quality gate screenshotları üretildi.

## Komut Sonuçları

### node_check_app

- Komut: `node --check src\webui\app.js`
- Return code: `0`
- Süre: `0.04s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `n/a`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\node_check_app.txt`

```text
(çıktı yok)
```

### pytest

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe -m pytest`
- Return code: `0`
- Süre: `8.06s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `n/a`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\pytest.txt`

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\Pc\Documents\New project\production-bot
configfile: pytest.ini
testpaths: tests
collected 189 items

tests\test_bulk_gallery_flow.py ...                                      [  1%]
tests\test_clean_customer_demo_seed.py ....                              [  3%]
tests\test_combined_production_flow.py .....                             [  6%]
tests\test_customer_order_api.py ...                                     [  7%]
tests\test_layout_learning_engine.py ......                              [ 11%]
tests\test_mvp_safety.py ............................................... [ 35%]
........................................................................ [ 74%]
.                                                                        [ 74%]
tests\test_output_queue_metadata_reliability.py ...                      [ 76%]
tests\test_trendyol_order_to_production.py ............................. [ 91%]
................                                                         [100%]

============================= 189 passed in 6.68s =============================
```

### label_models_real_click_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\label_models_real_click_gate.py`
- Return code: `0`
- Süre: `23.05s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\label_models_real_click_gate.txt`

```text
...k_gate\\label_models_selected_detail.png",
    "preview_modal": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_models_click_gate\\label_models_preview_modal.png",
    "new_model_modal": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_models_click_gate\\label_models_new_model_modal.png",
    "clone_model_modal": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_models_click_gate\\label_models_clone_model_modal.png",
    "preview_binding_modal": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_models_click_gate\\label_models_preview_binding_modal.png",
    "health_check": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_models_click_gate\\label_models_health_check.png",
    "empty_filter": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_models_click_gate\\label_models_empty_filter.png",
    "missing_preview_filter": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_models_click_gate\\label_models_missing_preview_filter.png",
    "technical_mode_open": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_models_click_gate\\label_models_technical_mode_open.png"
  },
  "final_state": {
    "activePage": "labelModels",
    "selectedPath": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\02_a_gold.json",
    "selectedName": "02 Gold Cyzella AI Kabul Test Modeli",
    "manualTemplate": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\02_a_gold.json",
    "modelCount": 4,
    "visibleCards": 4,
    "selectedCardCount": 1,
    "newModelModalOpen": true,
    "newModelWizardStepCount": 5,
    "newModelWizardFieldPreview": true,
    "cloneModelModalOpen": false,
    "previewModalOpen": false,
    "bindingModalOpen": false,
    "healthResultVisible": true,
    "repairResultVisible": true,
    "technicalMode": true,
    "technicalVisible": true,
    "status": "Model kontrol edildi.",
    "editTemplateCalls": 0,
    "sourceModelCalls": 0,
    "consoleErrors": []
  }
}
```

### studio_canvas_interaction_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\studio_canvas_interaction_gate.py`
- Return code: `0`
- Süre: `27.5s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\studio_canvas_interaction_gate.txt`

```text
..."placeholder": "{{LABEL_TEXT}}",
        "excel_column": "label_text",
        "x_mm": "8.8",
        "y_mm": "12",
        "width_mm": "30",
        "height_mm": "6",
        "font_family": "Segoe UI",
        "font_path": "",
        "font_size": "14",
        "letter_spacing": 0,
        "line_height": 1.18,
        "color": "#111111",
        "bold": false,
        "italic": false,
        "align": "center",
        "vertical_align": "middle",
        "visible": true,
        "font_preset_id": "",
        "auto_fit_enabled": false,
        "min_font_size": "",
        "max_font_size": ""
      }
    },
    {
      "name": "date_text_drag",
      "status": "PASSED",
      "before": {
        "field_name": "Tarih",
        "field_type": "Tarih",
        "excel_column": "date_text",
        "x_mm": "17",
        "y_mm": "17",
        "width_mm": "16",
        "height_mm": "4",
        "font_family": "Segoe UI",
        "font_path": "",
        "font_size": "8",
        "line_height": "",
        "color": "#111111"
      },
      "after": {
        "field_name": "Tarih",
        "field_type": "Tarih",
        "excel_column": "date_text",
        "x_mm": "18.9",
        "y_mm": "18",
        "width_mm": "16",
        "height_mm": "4",
        "font_family": "Segoe UI",
        "font_path": "",
        "font_size": "8",
        "line_height": "",
        "color": "#111111"
      }
    },
    {
      "name": "note_text_drag",
      "status": "PASSED",
      "before": {
        "field_name": "Not",
        "field_type": "Not",
        "excel_column": "note_text",
        "x_mm": "12",
        "y_mm": "21",
        "width_mm": "26",
        "height_mm": "4",
        "font_family": "Segoe UI",
        "font_path": "",
        "font_size": "8",
        "line_height": "",
        "color": "#111111"
      },
      "after": {
        "field_name": "Not",
        "field_type": "Not",
        "excel_column": "note_text",
        "x_mm": "13.9",
        "y_mm": "22",
        "width_mm": "26",
        "height_mm": "4",
        "font_family": "Segoe UI",
        "font_path": "",
        "font_size": "8",
        "line_height": "",
        "color": "#111111"
      }
    }
  ]
}
```

### print_action_real_user_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\print_action_real_user_gate.py`
- Return code: `0`
- Süre: `10.53s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\print_action_real_user_gate.txt`

```text
...       "top": 370.72918701171875,
            "left": 209.33334350585938,
            "width": 715.3333740234375,
            "height": 195.9375
          },
          "dock": {
            "top": 341.3958435058594,
            "left": 956.6666870117188,
            "width": 298.66668701171875,
            "height": 369.9375
          },
          "scrollY": 0,
          "mainScroll": 0,
          "statusCount": 0
        },
        "after": {
          "studio": {
            "top": 153.39584350585938,
            "left": 86,
            "width": 1188,
            "height": 614.6041870117188
          },
          "topbar": {
            "top": 153.39584350585938,
            "left": 94,
            "width": 1172,
            "height": 118
          },
          "canvas": {
            "top": 370.72918701171875,
            "left": 209.33334350585938,
            "width": 715.3333740234375,
            "height": 195.9375
          },
          "dock": {
            "top": 341.3958435058594,
            "left": 956.6666870117188,
            "width": 298.66668701171875,
            "height": 369.9375
          },
          "scrollY": 0,
          "mainScroll": 0,
          "statusCount": 0
        }
      }
    },
    {
      "name": "manual_pdf_added_to_queue",
      "status": "PASSED",
      "details": {
        "ok": true,
        "queueCount": 358,
        "pdf": "output/2026-05-20/print/manual/2026-05-20_01-A-Gold-Rulo-Etiket_Stale-Kontrol_50x30_1adet_batch.pdf"
      }
    },
    {
      "name": "queue_safe_print_modal",
      "status": "PASSED",
      "details": {
        "ok": true,
        "title": "Yazdırmaya Hazır",
        "details": "MODEL\n01 A Gold Rulo Etiket\nİSİM\nStale Kontrol\nTARİH\n-\nNOT\n-\nÖLÇÜ\n50 x 30 mm\nADET\n1\nPDF\n2026-05-20_01-A-Gold-Rulo-Etiket_Stale-Kontrol_50x30_1adet_batch.pdf",
        "buttons": [
          "PDF’i Gör",
          "Yazdır",
          "İptal"
        ]
      }
    },
    {
      "name": "no_silent_print_ui",
      "status": "PASSED",
      "details": {
        "ok": true,
        "directPrintOff": true,
        "openText": true,
        "hasSilentPrint": false,
        "openedExternal": ""
      }
    }
  ]
}
```

### production_history_real_user_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\production_history_real_user_gate.py`
- Return code: `0`
- Süre: `12.11s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\production_history_real_user_gate.txt`

```text
...         \n            Preflight: WARNING\n            Çıktı doğrulama: OK\n            Queue: NOT_QUEUED\n          \n          \n            PDF’i Gör\n            PNG Önizle\n            Tekrar Sıraya Ekle\n            Aynı Bilgilerle Studio’da Aç\n          \n        \n      \n        \n          01 A Gold Rulo Etiket\n          2026-05-14 11:30:07 · Yazdir Test · 1 adet · 50.0 x 30.0 mm\n          \n            Preflight: WARNING\n            Çıktı doğrulama: OK\n            Queue: NOT_QUEUED\n          \n          \n            PDF’i Gör\n            PNG Önizle\n            Tekrar Sıraya Ekle\n            Aynı Bilgilerle Studio’da Aç\n          \n        \n      ",
        "hasSearch": true,
        "hasModelFilter": true,
        "hasQueueFilter": true,
        "hasValidationFilter": true,
        "hasDateFilters": true,
        "hasOpenStudioButton": true,
        "hasQueueButton": true,
        "selectedTemplate": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\01_a_gold.json",
        "manualText": "Sedef Sefer",
        "manualDate": "01.07.2026",
        "manualNote": "Tepsi Üzeri",
        "queueModalOpen": false,
        "queueModalText": "Etiket işi güvenli şekilde yazdırma sırasına alındı. Yazıcı otomatik çalışmaz; PDF’i kontrol ettikten sonra manuel yazdırabilirsiniz.",
        "queueModalFile": "",
        "consoleErrors": []
      }
    },
    {
      "name": "history_requeues_validated_pdf",
      "status": "PASSED",
      "state": {
        "status": "EXISTS",
        "message": "Bu etiket işi zaten yazdırma sırasında.",
        "id": "764b9f47cca445288f883d6f91207019"
      }
    }
  ],
  "screenshots": {
    "history_page": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\production_history_gate\\production_history_page.png",
    "history_opened_in_studio": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\production_history_gate\\production_history_opened_in_studio.png",
    "history_requeue_backend_result": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\production_history_gate\\production_history_requeue_backend_result.png"
  }
}
```

### label_outputs_gallery_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\label_outputs_gallery_gate.py`
- Return code: `0`
- Süre: `11.57s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\label_outputs_gallery_gate.txt`

```text
...  "hasDateFilter": true,
        "hasStudioAction": false,
        "hasReadyStudioAction": false,
        "hasReproduceAction": false,
        "hasFolderAction": false,
        "hasQueueAction": false,
        "technicalDetailsOpen": false,
        "manualTemplate": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\01_a_gold.json",
        "manualText": "Ayşe & Mehmet",
        "manualDate": "12.05.2026",
        "manualNote": "Söz Hatırası",
        "statusText": "",
        "consoleErrors": []
      }
    },
    {
      "name": "technical_archive_separated",
      "status": "PASSED",
      "state": {
        "activePage": "labelOutputs",
        "outputCount": 17,
        "customerOutputCount": 0,
        "cardCount": 0,
        "technicalCardCount": 17,
        "summaryText": "Toplam Çıktı\n0\nDoğrulanmış müşteri dosyaları\nPDF\n0\nPDF dosyaları\nPNG\n0\nGörsel önizlemeler\nBatch PDF\n0\nToplu çıktı\nBugünkü Çıktı\n0\nBugün oluşturulan\nYazdırma Sırasında\n0\nQueue’da bekleyen\n\nHenüz müşteri çıktısı yok. Etiket Studio veya Toplu Etiket ekranından çıktı oluşturun.",
        "previewText": "Listeden bir çıktı seçin.\nPDF/PNG önizlemesi burada görünecek.",
        "hasSearch": true,
        "hasTypeFilter": true,
        "hasModelFilter": true,
        "hasDateFilter": true,
        "hasStudioAction": false,
        "hasReadyStudioAction": false,
        "hasReproduceAction": false,
        "hasFolderAction": false,
        "hasQueueAction": false,
        "technicalDetailsOpen": false,
        "manualTemplate": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\templates\\designs\\01_a_gold.json",
        "manualText": "Ayşe & Mehmet",
        "manualDate": "12.05.2026",
        "manualNote": "Söz Hatırası",
        "statusText": "",
        "consoleErrors": []
      }
    }
  ],
  "screenshots": {
    "gallery_page": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_outputs_gallery_gate\\label_outputs_gallery_page.png",
    "gallery_technical_archive": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\label_outputs_gallery_gate\\label_outputs_technical_archive.png"
  }
}
```

### settings_security_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\settings_security_gate.py`
- Return code: `0`
- Süre: `13.32s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\settings_security_gate.txt`

```text
...en son backup dosyası raporlarda ve işlem sonucunda belirtilir.\nSon ayar backup geçmişi\n2026-05-20 04:08 · settings_20260520_040807.yaml · 1 KB\n2026-05-19 21:47 · settings_20260520_040805.yaml · 1 KB\n2026-05-19 21:47 · settings_20260519_214713.yaml · 1 KB\n2026-05-19 21:25 · settings_20260519_214709.yaml · 1 KB\n2026-05-19 21:25 · settings_20260519_212549.yaml · 1 KB\n2026-05-19 20:57 · settings_20260519_212546.yaml · 1 KB\n2026-05-19 20:57 · settings_20260519_205743.yaml · 1 KB\n2026-05-19 20:44 · settings_20260519_205736.yaml · 1 KB",
        "folderText": "Çıktı klasörü\noutput/2026-05-20\nPDF/PNG müşteri çıktıları\noutput/YYYY-MM-DD/print ve preview klasörleri\nBackup klasörü\nconfig/backups ve model backups klasörleri\nKaynak dosyalar\nAI/CDR kaynakları overwrite edilmez",
        "fontColorText": "Varsayılan font\nEtiket Studio içinden seçilir; teknik font yolu normal kullanıcıya gösterilmez.\nMarka renkleri\nCyzella Gold, Cream, Brown, Burgundy ve Soft Pink paletleri Studio’da kullanılır.\nKontrast kontrolü\nZayıf okunurlukta kullanıcıya baskı uyarısı gösterilir.",
        "widthInput": "40",
        "heightInput": "40",
        "rollWidthInput": "40",
        "rollGapInput": "3",
        "saveStatus": "",
        "hasSaveButton": true,
        "hasAdvancedButton": true,
        "directPrintAllowed": false,
        "defaults": {
          "media_type": "ROLL",
          "label_width_mm": 40,
          "label_height_mm": 40,
          "roll_gap_mm": 3,
          "printer_dpi": 300,
          "default_copies": 1,
          "horizontal_offset_mm": 0,
          "vertical_offset_mm": 0,
          "scale_percent": 100,
          "safe_margin_mm": 1.5,
          "background_enabled": true,
          "show_cut_boundary": false,
          "show_order_number_on_label": false,
          "roll_width_mm": 40
        }
      }
    }
  ],
  "screenshots": {
    "settings_page": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\settings_security_gate\\settings_security_center_page.png",
    "settings_after_save": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\settings_security_gate\\settings_after_save.png"
  }
}
```

### help_onboarding_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\help_onboarding_gate.py`
- Return code: `0`
- Süre: `11.89s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\help_onboarding_gate.txt`

```text
...       "tourTitle": "Yazıya tıkla",
        "tourBody": "\n      Yazıya tıkla\n      Etiket Studio’da İsim, Tarih veya Not katmanına tıklayın. Seçili alan mavi çerçeve ve rozetle görünür.\n      Hedef ekran: Etiket Studio\n    ",
        "shortcutText": "\n        \n          ArrowSeçili yazıyı 0.1 mm taşır.\n          Shift + ArrowSeçili yazıyı 1 mm taşır.\n          Alt + ArrowSeçili yazıyı 0.05 mm hassas taşır.\n          Ctrl + ZGeri alır.\n          Ctrl + Yİleri alır.\n          DeleteEk yazı alanını siler; temel alanlarda onay ister.\n        \n      ",
        "fixesText": "\n        \n          Görsel eksikEtiket Modelleri’nde modeli seçip Görsel Bağla ile PNG/JPG/WebP/SVG/PDF önizleme ekleyin.Model sayfasına git\n          Yazı sığmıyorEtiket Studio’da Yazıları Sığdır veya Fontu Otomatik Küçült komutunu kullanın.Studio’ya git\n          PDF oluşturulamadıÖnce Çıktı Kontrolü yapın. Background ve İsim/Tarih/Not alanlarının görünür olduğundan emin olun.Çıktı kontrolüne git\n          Queue’ya eklenemediSon PDF/PNG güncel ve validation geçmiş olmalı. Gerekirse yeniden PDF/PNG oluşturun.Sırayı gör\n        \n      ",
        "checklistHidden": true,
        "checklistText": "\n        \n          Tek EtiketModel seçildiİsim / Tarih / Not kontrol edildiPDF/PNG oluşturuldu ve önizlendi\n          Toplu ExcelExcel kontrol edildiHatalı satırlar düzeltildi veya çıkarıldıBatch PDF sıraya doğru eklendi\n          YazdırmaYazıcı otomatik çalışmazPDF kullanıcı onayıyla açılırİş bittiyse Yazdırıldı işaretlenir\n        \n      ",
        "hasTargetButton": true,
        "consoleErrors": []
      }
    }
  ],
  "screenshots": {
    "help_tour": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\help_onboarding_gate\\help_tour.png",
    "help_shortcuts": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\help_onboarding_gate\\help_shortcuts.png",
    "help_fixes": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\help_onboarding_gate\\help_fixes.png",
    "help_checklist": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\help_onboarding_gate\\help_checklist.png"
  }
}
```

### real_production_quality_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\real_production_quality_gate.py`
- Return code: `0`
- Süre: `0.62s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\real_production_quality_gate.txt`

```text
...-20/print/manual/2026-05-20_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_2.pdf",
  "queue_result": {
    "status": "ADDED",
    "message": "Etiket işi yazdırma sırasına eklendi.",
    "id": "a0e589d598d642dfb44272c8ea845c0f"
  },
  "pdf_preview_payload": {
    "status": "OK",
    "page_count": 1,
    "preview_pages": [
      {
        "page": 1,
        "preview_png_path": "output/2026-05-20/preview/pdf/2026-05-20_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_2/page_001.png",
        "preview_url": "file:///C:/Users/Pc/Documents/New%20project/production-bot/output/2026-05-20/preview/pdf/2026-05-20_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_batch_2/page_001.png"
      }
    ]
  },
  "validations": {
    "png": {
      "status": "PASSED",
      "reason": "",
      "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\print\\manual\\2026-05-20_01-A-Gold-Rulo-Etiket_Ayse-Mehmet-QA_50x30_1adet_2.png",
      "size": 138866,
      "width": 591,
      "height": 354,
      "colorful_pixels": 678,
      "dark_pixels": 126,
      "field_dark_pixels": {
        "label_text": 57,
        "note_text": 63,
        "date_text": 15
      }
    },
    "pdf_page": {
      "status": "PASSED",
      "reason": "",
      "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\quality_gate\\quality_gate_pdf_page.png",
      "size": 302158,
      "width": 900,
      "height": 539,
      "colorful_pixels": 582,
      "dark_pixels": 72,
      "field_dark_pixels": {
        "label_text": 37,
        "note_text": 52,
        "date_text": 7
      }
    },
    "real_preview": {
      "status": "PASSED",
      "reason": "",
      "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\preview\\manual_label\\manual_preview_01_a_gold_Ayse_Mehmet_QA.png",
      "size": 138866,
      "width": 591,
      "height": 354,
      "colorful_pixels": 678,
      "dark_pixels": 126,
      "field_dark_pixels": {
        "label_text": 57,
        "note_text": 63,
        "date_text": 15
      }
    },
    "files_are_fresh": {
      "status": "PASSED",
      "started_at": 1779239301.583696
    }
  }
}
```

### final_acceptance_gate

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\final_acceptance_gate.py`
- Return code: `0`
- Süre: `1.02s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `PASSED`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\final_acceptance_gate.txt`

```text
...\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\quality_gate\\2026-05-20_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_batch_pdf_page.png",
      "validations": {
        "png": {
          "status": "PASSED",
          "reason": "",
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\print\\manual\\2026-05-20_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet.png",
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
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\quality_gate\\2026-05-20_Final-QA-Kabul-Modeli_Ayse-Mehmet-QA_50x30_1adet_batch_pdf_page.png",
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
          "path": "C:\\Users\\Pc\\Documents\\New project\\production-bot\\output\\2026-05-20\\preview\\manual_label\\manual_preview_04_a_qa_Ayse_Mehmet_QA.png",
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
          "started_at": 1779239302.744603
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

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\capture_webui_screenshots.py`
- Return code: `0`
- Süre: `61.27s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `n/a`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\capture_webui_screenshots.txt`

```text
(çıktı yok)
```

### capture_quality_gate_screenshots

- Komut: `C:\Users\Pc\Documents\New project\production-bot\.venv\Scripts\python.exe scripts\capture_quality_gate_screenshots.py`
- Return code: `0`
- Süre: `12.89s`
- Timeout: `420s`
- Zaman aşımı: `hayır`
- JSON status: `n/a`
- Sonuç: `PASSED`
- Log: `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\test_command_real_user_qa\capture_quality_gate_screenshots.txt`

```text
(çıktı yok)
```

## Screenshot Yolları

- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\ui_screenshots`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\quality_gate`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\label_models_click_gate`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\studio_interaction`
- `C:\Users\Pc\Documents\New project\production-bot\output\2026-05-20\print_action_gate`

## P0/P1 Durumu

P0/P1 hata yok.

## Kalan Riskler

- Runner otomatik kalite kapılarını çalıştırır; kullanıcı manuel olarak farklı bir davranış görürse kullanıcı gözlemi esas alınır.
- P0/P1 fail olursa Codex düzeltme yapıp runner'ı tekrar çalıştırmalıdır.
