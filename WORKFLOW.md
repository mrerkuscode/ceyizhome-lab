# WORKFLOW — Multi-Claude / Multi-Tool Calisma Deseni

> Bu dosya farkli Claude/araclarin projede nasil koordineli calistigini anlatir.
> Kaynak: CLAUDE.md + START_HERE_FOR_CODEX.md + CODEX_LEAD_DEVELOPER_MANUAL.md

## Roller

Projede birden fazla yapay zeka araci ve insan birlikte calisir. Once kim oldugunu belirle:

- Claude Code (Terminal): Lokal kod yazma, test calistirma, git islemleri.
- Claude Chrome (Tarayici): Gorsel inceleme, GitHub edit, PR inceleme/merge, canli localhost testi.
- Web Claude (claude.ai): Plan, prompt ve mockup hazirligi.
- Codex (Lead Developer): Ana gelistirici, UI/UX denetcisi, QA ve release kalite kontrol sorumlusu (kendi rehber dosyalarini izler).
- Insan (mrerkuscode): Sahibi; merge, gercek yazdirma ve uretim onaylarini verir.

## Her Gorevde Ilk Sira

1. CLAUDE.md oku — kim oldugunu belirle.
2. PROJECT_CONTEXT.md oku — genel baglam.
3. ACTIVE_SPRINT.md oku — su an ne yapiliyor.
4. FORBIDDEN.md oku — yasaklari kontrol et.
5. Gorev render/output/queue/guvenlik iceriyorsa ilgili standart/docs dosyasini oku.
6. Once P0/P1 risk var mi bak; varsa yeni ozellik ekleme.

## Branch ve PR Deseni

- Her is icin ayri branch acilir (ornek: docs/..., fix/..., feat/...).
- Her degisiklik commit + PR olarak gonderilir; main'e dogrudan push tercih edilmez.
- PR aciklamasi: ne degisti, neden, hangi dosyalar, test/etki, kalan risk.
- Merge yetkisi insandadir. Claude/Codex kendi PR'ini merge etmez; insan onayini bekler.
- Turkce karakterler UTF-8 olmali (BOM yok).

## P0/P1/P2/P3 Onceligi

- P0: Uretim akisini bozan kritik hata (PDF/PNG canvas'tan farkli, isim/tarih/background kayboluyor, buton sessiz, yanlis model, queue stale, Turkce karakter bozuk, guvenlik riski). Once bunlar duzeltilir.
- P1: selectedModel kaybi, yanlis yonlendirme, preview/model secimi, olcu override, drag/resize calismiyor, gercek click testi eksik.
- P2: UX zayifligi (bos state, belirsiz buton isimleri, zayif kartlar).
- P3: Buyuk ozellik, uzun vadeli roadmap, mimari genisleme.

Kural: P0/P1 varken yeni ozellik eklenmez. Once stabil MVP, sonra P2 UX, sonra P3.

## Calisma Dongusu

1. Raporlari ve baglami oku.
2. Ilgili dosyalari bul.
3. P0/P1 riskleri sinifla.
4. Kucuk, guvenli degisiklik yap.
5. Test ekle veya guncelle.
6. Gercek kullanici davranisini simule et (click, drag/resize, PDF/PNG, queue).
7. Screenshot al.
8. Komutlari calistir.
9. Kendi yaptigini tekrar kontrol et.
10. Hata kaldiysa tekrar duzelt.
11. Raporla.

## Sahte Basari Sayilmaz

Su durumlar basari degildir: toast ciktiki ama gercek islem yok, modal yanlis veri gosterdi, PDF eski dosya, PNG'de background yok, queue'ya yanlis dosya eklendi, test sadece buton var mi diye bakti, handle gorunuyor ama drag/resize calismiyor, screenshot alinmadi, console error var.

## Standart Komutlar (referans)

Kapsam render/output/queue'yu etkiliyorsa kalite kapilari zorunludur:

    node --check src\webui\app.js
        .venv\Scripts\python.exe -m pytest
            .venv\Scripts\python.exe scripts\real_production_quality_gate.py
                .venv\Scripts\python.exe scripts\final_acceptance_gate.py
                    .venv\Scripts\python.exe scripts\capture_webui_screenshots.py

                    ## Manuel Karar / Onay Gerektirenler

                    Asagidakiler otomatik yapilmaz; dur ve insan onayi iste (detay FORBIDDEN.md):
                    direct print acmak, yaziciyi otomatik calistirmak, lazer/RDWorks otomasyonu, Corel/Illustrator native edit'i uretime almak, kaynak AI/CDR degistirmek, buyuk refactor, yeni framework eklemek.
                    
