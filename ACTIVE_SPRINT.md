# ACTIVE_SPRINT — Aktif Sprint Durumu

> Bu dosya su an ne yapildigini takip eder. CLAUDE.md'den sonra okunur ve duzenli guncellenir.
> Kaynak (son snapshot): CODEX_CURRENT_PRIORITY.md (Updated: 2026-05-17). Guncel sira icin o dosya da kontrol edilir.

## Durum Ozeti

- Branch: main
- MVP: ~%99
- Test: 68/68 PASS (CI dahil)
- Bilinen P0: yok
- Bilinen P1: yok (dogrulanmis lokal kapilarda)

## Son Tamamlananlar

- Trendyol soru/mesaj kaniti dayanikliligi guclendirildi; manuel "Sorulari Oku" bekleyen + cevaplanmis sorulari birlikte okuyup dedupe ediyor ve read-only kanit olarak sakliyor.
- Trendyol soru servisi kapaliysa son deneme durumu ve temizlenmis hata mesaji UI'da "kanit yok / servis yanit vermiyor" olarak aciklaniyor.
- Trendyol hizli filtrelerine "Kanit Bekliyor" ve "Onay Bekliyor" eklendi.
- Katalog eslestirme onerileri iyilestirildi; canli refresh: 332 oneri (327 label, 3 label_and_name_cut, 2 review) ve hepsi kullanici onayi bekliyor.
- Model secilmeden katalog onerisi onaylanmiyor (backend NEEDS_MODEL korumasi).
- Etiket Studio Hizli Uretim / Gelismis Duzenleme modu eklendi; layout stabilite kapisi gecildi.
- PDF/PNG render, output validation ve queue zinciri kalite kapilarindan gecti.

## Aktif / Siradaki 3 Oncelik (kullanici testi)

1. Trendyol > Urun Eslestirme tabinda arama/filtre ile 5-10 gercek urunu model veya isim kesim tipiyle eslestirmek.
2. Trendyol > Siparisler tabinda soru kaniti gorunen bir satiri "Bu metinden alanlari kullan" > "Onayla ve Uretime Hazir Yap" > "Uretime Aktar" akisiyla denemek.
3. Aktarilan satiri Studio / Toplu Etiket / Isim Kesim akisi ve PDF/PNG/Queue zincirinde gercek gozle kontrol etmek.

## Kalici Gercek Kullanici Test Kilidi

- Rapor PASSED yazsa bile gercek kullanici akisi test edilir.
- P0/P1 kalirsa gorev bitmis sayilmaz.
- Buton gorunuyorsa tiklanir; sessiz kaliyorsa hata sayilir.
- Drag, resize, PDF/PNG, queue ve yazdirma onay akisi gercek davranisla dogrulanir.
- Kisa "test" komutu kapisi: scripts/run_test_command_real_user_qa.py
- Studio mouse/drag/resize kilidi: scripts/studio_canvas_interaction_gate.py
- Etiket Modelleri gercek click kilidi: scripts/label_models_real_click_gate.py

## Guvenlik Teyidi (son pass)

RDWorks acilmadi, lazer baslamadi, direct print acilmadi, yazici sessizce baslamadi, CorelDRAW/Illustrator acilmadi, kaynak AI/CDR degismedi, eski Trendyol projesi degismedi.

## Not

Bu dosya sprint ilerledikce guncellenmelidir. Detayli guncel oncelik ve calistirilan komut listesi icin CODEX_CURRENT_PRIORITY.md'ye bakin.
