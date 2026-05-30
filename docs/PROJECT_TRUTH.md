# CeyizHome Lab / Cyzella Production Studio — PROJE GERÇEK DURUM & YOL HARİTASI

> **Bu dosya projenin tek doğruluk kaynağıdır.** Her oturuma bununla başlanır.
> Her *doğrulanmış* değişiklikten sonra güncellenir (kod var → değil, çıktı doğru → güncelle).
>
> Son güncelleme: 2026-05-30
> Kaynak: Code kod-denetimi + Chrome runtime-denetimi + extraction teşhisi + görsel denetim (4 rapor birleştirildi)

---

## 0. Proje Nedir
Yerel (Windows) bir üretim aracı. Üretim Excel'ini okur → doğrular → baskı (PDF/PNG, rulo etiket), lazer (plaka tabanlı SVG) ve rapor (CSV) üretir. **Asla** CorelDRAW/yazıcı/RDWorks/lazeri otomatik açmaz. Güvenlik: sahte isim yok, üretimden önce operatör onayı, NEEDS_REVIEW satırları bloke. Birincil arayüz tarayıcı (localhost:8000); masaüstü (PySide) aynı arayüzü kullanır.

---

## 1. Gerçek Mimari
- **Tek ön-yüz:** `src/webui/index.html` + `app.js`. Masaüstü `file://`, Flask `localhost:8000` — ikisi de **aynı dosya**. UI değişikliği ikisini birden etkiler.
- **Transport ayrımı:** yalnızca `src/webui/api_adapter.js` içinde. Masaüstü = QWebChannel, tarayıcı = `fetch` → `/api/`.
- **Backend:** `src/server` (routes.py, controller_proxy.py), `src/intelligence` (Trendyol çıkarım), `label_designer`, lazer modülleri.
- **Çift transport boşluğu:** ~155 QWebChannel metoda karşılık ~50 `/api/` rota → **~105 yetenek tarayıcıda yok**. (Native-only olanlar kasıtlı istisna: klasör aç, native dialog vb.)

---

## 2. Modül Durumu (DOĞRULANMIŞ)

| Modül | Durum | Kanıt / Not |
|---|---|---|
| Ana Sayfa | ✅ | Gerçek veri (4 PDF/2 PNG), Son İşler, Model Durumu canlı |
| Etiket Modelleri | ✅ | 4 model, badge'ler doğru, detay paneli çalışıyor |
| Etiket Studio | 🟡 | Çalışıyor ama **sol araç çubuğu 8px'e çökmüş (araçlar görünmüyor)**, topbar taşıyor |
| Toplu Üretim Studio | ✅ | 6 adım wizard, Excel/Trendyol kaynak seçimi |
| İsim Kesim (Lazer) | ✅ | Çalışıyor; generatif weld/nesting **kasıtlı KAPALI** ("kütüphaneci" modu) |
| Yazdırma Sırası | ✅ | Boş kuyruk, sayaçlar doğru, "yazıcı otomatik çalışmaz" uyarısı |
| Müşteri Siparişleri | ⚠️ | "0 sipariş" — **persist BELİRSİZ, olası veri kaybı (araştırılmalı)** |
| Trendyol — transport | ✅ | PR #12 ile düzeldi; 3 buton 200, read-only sync çalışıyor (501 msg / 118 sipariş) |
| **Trendyol — AI isim/tarih çıkarımı** | 🔴 | **Tarih ✅ ama isim ~%30-35 isabet. Sistemik bozuk.** Selamlama/fiil/iyelik yakalıyor, %87 yanlış güven, review'e gitmiyor |
| İsim Doğrulama | ⚠️ | Kuyruk hiç dolmuyor; tetikleme koşulu belirsiz |
| Raporlar | ⚠️ | "Veri köprüsü bulunamadı" — tüm sekmeler boş |
| Ayarlar ve Güvenlik | ✅ | Tüm sekmeler render |

---

## 3. Bilinen Sorunlar (öncelikli)

### 🔴 P1 — kritik
- **Trendyol isim çıkarımı sistemik bozuk** (~%30-35 isabet). Yaklaşım-seviyesi rebuild gerek (AI-öncelikli, niyet-anahtarlı, dürüst güven, review-kapısı). Stopword yaması yetmez.
- **`.order-product-thumb` 1200×1800px dev kutu** → sipariş kartı 2050px, sayfa kullanılamaz.
- **Müşteri Siparişleri persist belirsiz** → olası veri kaybı. Önce araştır.
- **Etiket Studio sol araç çubuğu 8px'e çökmüş** — araçlar işlevsiz görünüyor.

### 🟠 P2 — yüksek
- Tasarım pattern'leri: `max-width` yok (sprawl), sayfa değişince scroll sıfırlanmıyor, dikey stat/filtre yığılması, `page-head` tutarsız (74–240px), topbar şişmiş (81px), Trendyol grid 167px taşıyor, Studio topbar 366px taşıyor.
- **Güven skoru kalibrasyonu bozuk** (%87 yanlışa, %84 doğruya).
- İsim Doğrulama kuyruğu tetikleme koşulu belirsiz.
- Raporlar veri köprüsü.
- **Parite boşluğu** ~105 yetenek tarayıcıda yok (tek-merkez birleştirme ile çözülecek).

### 🟡 P3 — orta/cila
- #9 altın çizgi toggle, #10 kenarlık renk/kalınlık, #11 yardım rehberi.
- Test boşlukları: "Merhba" typo testi yok, "isim yazılacak" tekil pattern testi yok, CorelDRAW-hiç-çağrılmıyor mimari testi yok.
- Kontrol Kuyruğu header hücreleri DOM'da yok (erişilebilirlik).

---

## 4. Yol Haritası (son aşamaya kadar)

> Sıra önerilebilir; B ile A bağımsız (farklı dosyalar) → paralel gidebilir.

**Faz 0 — Dal konsolidasyonu.** Merge bekleyen dalları main'e al (bkz. §6). Amaç: main = gerçek.
*Bitti kriteri:* açık iş dalı kalmadı, main çalışan kodu yansıtıyor.

**Faz B — Tasarım düzeltme (Batch 1 + 2).** Görsel denetimin pattern + kritik fix'leri. `.order-product-thumb`, max-width, scroll-reset, grid'ler, Studio toolbar (işlevsel).
*Bitti kriteri:* hiçbir sayfada taşma/dev kutu yok, Chrome görsel onayı.

**Faz A — Trendyol isim/tarih çıkarımı REBUILD.** Çekirdek bozuk özellik. AI-öncelikli, niyet-anahtarlı ("X isim yazılacak"→isim=X), selamlama/sipariş-no/şablon eler, dürüst güven, belirsiz→NEEDS_REVIEW, asla uydurmaz.
*Bitti kriteri:* eldeki 51 gerçek mesajda yüksek isabet, çöp isim yok, güven kalibre, regresyon testleri eklendi.

**Faz C — Tek-merkez birleştirme (hedef A).** Masaüstünü localhost'a taşı, ~105 yeteneği rota yap, QWebChannel'ı native-only'ye indir, parite-guard testi.
*Bitti kriteri:* yeni özellik tek yerden ikisine birden; guard testi yeşil.

**Faz D — #2 Etiket üretimi + #3 İsim kesim doğruluğu.** Gerçek çıktıyla doğrula (testler iyi görünüyor; runtime'da teyit).
*Bitti kriteri:* gerçek sipariş → doğru PDF/PNG ve doğru SVG/DXF, Türkçe karakter, bağlı harf güvenli.

**Faz E — Kalanlar.** Müşteri Siparişleri persist, Raporlar veri köprüsü, İsim Doğrulama kuyruğu, güven kalibrasyonu, P2/P3'ler, test boşlukları.

---

## 5. Çalışma Disiplini (öğrenilen dersler)
- **fix → PR → MERGE → `git pull` → restart → ANCAK sonra Chrome doğrular.** (Yoksa eski main'i test ederiz — PR #12 dersi.)
- **"Kod var" yetmez, "çıktı doğru mu" diye bak.** (Extraction dersi: testler 262/262 geçti ama isim %30 isabetti.)
- **Dal hijyeni:** iş main'e merge edilmeden "bitti" sayılmaz.
- Rol dağılımı: Claude = plan/prompt + bu dosyayı günceller; Code = kod/test/git; Chrome = runtime/görsel/GitHub.

---

## 6. Açık Dallar (merge bekleyen)
| Branch | Commit | İçerik |
|---|---|---|
| chore-token-cleanup | 3 | Doc yeniden adlandırma, .gitignore |
| design/etiket-studio-toolbar-apply | 1 | Etiket Studio toolbar 3-grup uygulaması |
| docs/audit-roadmap | 1 | ROADMAP.md |
| (+ Faz B tasarım dalları açılacak) | | |

Diğer ~18 dal merge edilmiş ya da boş deney — güvenle silinebilir.

---

## 7. Test Durumu
262/262 (%97 pass). Dağılım: ~%15 sadece HTTP-200, ~%30 mock backend, ~%55 çıktı-doğruluğu (yüksek kalite: PDF üretimi, Türkçe isim, Trendyol kanıt-yoksa-isim-yok), ~20 güvenlik kapısı.
**Boşluk:** extraction edge-case'leri test edilmiyor (typo selamlama, "isim yazılacak" tekil pattern) — bug bu yüzden kaçtı. Faz A'da eklenecek.
