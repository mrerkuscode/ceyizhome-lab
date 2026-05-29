# PROJECT MASTER CONTEXT

## Proje

Ad: Cyzella Production Studio / Label Studio V1  
Yol: `C:\Users\Pc\Documents\New project\production-bot`

## Ürün Amacı

Normal kullanıcı için basit, hızlı ve güvenilir etiket üretim sistemi.

Temel akış:
1. Etiket modelini görselden seç.
2. İsim, tarih ve notu düzenle.
3. Yazıyı canvas üzerinde sürükle ve boyutlandır.
4. Canlı sonucu gör.
5. Gerçek render kontrolü yap.
6. PDF/PNG oluştur.
7. Yazdırma sırasına doğru dosyayı ekle.
8. PDF'i kontrol ettikten sonra manuel yazdır.

## Üst Düzey Ürün Sorumluluğu

Codex bu projede yalnızca verilen görevi yapan kod aracı değildir. Senior product builder gibi davranır:
- Eksikleri kullanıcı söylemeden fark eder.
- Her sayfayı normal kullanıcı gözüyle değerlendirir.
- Üretimi hızlandıran ama güvenli kalan iyileştirmeleri önerir ve uygular.
- Grafik, etiket tasarımı, UI/UX, QA ve release kalitesini birlikte düşünür.
- Raporu ilerleme saymaz; çalışan, test edilen, screenshot ile kanıtlanan akışı ilerleme sayar.

Her değişiklikte şu soru sorulur: "Bu gerçekten üretimi kolaylaştırıyor mu?"

## Ana Üretim Kararı

Günlük üretim yolu:

PNG/JPG/WebP/SVG/PDF tasarım görseli + program içi düzenlenebilir text layer + PDF/PNG/rulo batch çıktı.

CDR/AI native edit yalnızca teknik PoC alanında kalır. Ana üretim akışına bağlanmaz.

## Mevcut Çalışan Akışlar

Son kalite raporlarına göre:
- Ana Sayfa üretim merkezi haline getirildi.
- Etiket Modelleri gerçek click testleriyle doğrulandı.
- Etiket Studio canvas, drag, resize, keyboard ve zoom etkileşimleri doğrulandı.
- Canvas -> PDF/PNG -> Queue zinciri kalite kapısından geçti.
- Direct print kapalı.
- Teknik editör normal kullanıcı akışından izole.

Manuel kullanıcı gözlemi her zaman rapordan üstündür. Kullanıcı "çalışmıyor" diyorsa gerçek davranış tekrar test edilir.

## Güvenlik Sınırları

Yasak:
- CorelDRAW açmak
- Illustrator açmak
- RDWorks açmak
- Yazıcı çalıştırmak
- Lazer başlatmak
- Direct print aktif etmek
- Kaynak AI/CDR dosyalarını değiştirmek veya overwrite etmek
- Mock/stale veriyi final PDF/PNG çıktısına karıştırmak
- Normal kullanıcıyı teknik JSON/X/Y/font/path ekranlarına düşürmek

## Ana Sayfalar

- Ana Sayfa: üretim başlangıç merkezi.
- Etiket Modelleri: model katalog ve yönetim ekranı.
- Etiket Studio: ana tekli üretim ekranı.
- Toplu Etiket: Excel tabanlı üretim.
- Yazdırma Sırası: manuel yazdırma öncesi güvenli queue.
- Etiket Çıktıları: müşteri çıktıları ve preview.
- Ayarlar: varsayılan ölçü/rulo ayarı/config.
- Raporlar: teknik ve release raporları.
- Native AI/CDR Deneme: teknik PoC.
- Lazer: teknik bölüm, otomasyon yok.

## Bilinen Riskler

- QWebEngine testleri faydalı ama fiziksel mouse ve farklı ekran ölçeklerinde manuel QA halen değerlidir.
- Teknik Mod içindeki gelişmiş araçlar normal kullanıcıdan izole kalmalıdır.
- Render/output/queue zinciri çalışan kritik sistemdir; gereksiz refactor yapılmaz.
- Raporlarda PASSED yazsa bile kullanıcı manuel testte sorun görürse kullanıcı gözlemi kaynak kabul edilir.
