# Execution Prompt Sequence

## 1. Metadata ve Queue/Outputs güvenilirliği

Queue ve Etiket Çıktıları sayfalarında PDF dosya adından güvenli model/isim/ölçü/adet fallback'i, PNG preview pairing ve missing/stale PDF güvenlik testlerini tamamla. `verify_print_queue_flow.py`, `verify_outputs_gallery_flow.py`, `pytest`, quality gate ve screenshot capture çalıştır.

## 2. Toplu Etiket 100 satır final

100 satırlık Excel fixture ile galeri, modal düzenleme, Kaydet/Vazgeç/Sil, manifest, batch PDF/PNG ve queue doğrulamasını güçlendir. Özet kartları galeri state'iyle senkron olmalı.

## 3. Yeni Model Ekle final

Wizard footer, görsel yükleme, oran kontrolü, backup ve kaydet sonrası Studio açma akışını gerçek click scriptiyle doğrula.

## 4. Studio ve Modeller polish

Studio inspector/property bar responsive polish ve Etiket Modelleri preview/variant/technical mode edge-case testlerini çalıştır.

## 5. Yardım, doküman, final kabul

User manual, technical manual, release notes ve final checklist'i güncelle. Ardından tüm gerçek kullanıcı testleri ve screenshotları çalıştır.

## 6. RDWorks ayrı faz

Ana etiket MVP kabulünden sonra DXF birincil export, true text-to-path PoC, offset/stroke-to-path riski ve 50-100 isim packing iyileştirmesini ayrı fazda ele al.
