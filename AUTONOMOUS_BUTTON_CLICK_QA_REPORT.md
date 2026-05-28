# AUTONOMOUS BUTTON CLICK QA REPORT

Tarih: 2026-05-11

## Etiket Modelleri Gerçek Click Sonucu

`scripts/label_models_real_click_gate.py` sonucu: PASSED.

Doğrulanan kritik akışlar:

- Sayfa açılışı.
- Yenile sonrası model listesi ve selectedModel korunması.
- Kart seçimi sonrası sağ panel ve selectedModel güncellenmesi.
- Karttan “Etiket Hazırla” ile doğru modelin Etiket Studio’ya taşınması.
- Karttan “Studio’da Düzenle” ile doğru ikinci modelin Etiket Studio’ya taşınması.
- Önizle modalının açılması.
- Yeni Model Ekle sade modalının açılması.
- Varyant oluşturma modalının güvenli açılması.
- Tasarım/Görsel bağlama akışının teknik editör açmadan çalışması.
- Modeli Kontrol Et sonucunun görünmesi.
- Filtre ve empty state davranışı.
- Teknik Mod kapalıyken teknik detayların gizli, açıkken görünür olması.

## Güvenlik Kanıtı

- `editTemplateCalls`: 0
- `sourceModelCalls`: 0
- Console error: yok

## Screenshot Kanıtları

- `output/2026-05-11/label_models_click_gate/label_models_general.png`
- `output/2026-05-11/label_models_click_gate/label_models_selected_detail.png`
- `output/2026-05-11/label_models_click_gate/label_models_preview_modal.png`
- `output/2026-05-11/label_models_click_gate/label_models_new_model_modal.png`
- `output/2026-05-11/label_models_click_gate/label_models_preview_binding_modal.png`
- `output/2026-05-11/label_models_click_gate/label_models_technical_mode_open.png`

## Kalan Risk

Kalan P0/P1 button regression yok.
