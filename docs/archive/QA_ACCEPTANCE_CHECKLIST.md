# QA ACCEPTANCE CHECKLIST

Her görev sonrası bu listeyi kullan.

## Genel

- [ ] P0 hata var mı?
- [ ] P1 hata var mı?
- [ ] Console error var mı?
- [ ] Türkçe karakterler doğru mu?
- [ ] Teknik detay normal kullanıcıya görünüyor mu?
- [ ] Sessiz kalan buton var mı?
- [ ] Değişiklik gerçek üretimi kolaylaştırıyor mu?
- [ ] Kullanıcı bir sonraki adımı ek açıklama olmadan anlayabilir mi?
- [ ] Sadece toast/modal değil, gerçek işlem doğrulandı mı?
- [ ] Gerekliyse gerçek click, pointer veya output testi var mı?
- [ ] Screenshot kanıtı üretildi mi?

## Güvenlik

- [ ] CorelDRAW açılmadı.
- [ ] Illustrator açılmadı.
- [ ] RDWorks açılmadı.
- [ ] Yazıcı çalışmadı.
- [ ] Lazer başlamadı.
- [ ] Direct print aktif edilmedi.
- [ ] Kaynak AI/CDR değişmedi.

## Etiket Modelleri

- [ ] Kart tıklama selectedModel güncelliyor.
- [ ] Etiket Hazırla doğru modeli Studio'ya taşıyor.
- [ ] Studio'da Düzenle doğru modeli açıyor.
- [ ] Önizle modal açıyor.
- [ ] Görsel Bağla teknik editör açmıyor.
- [ ] Yeni Model Ekle sade modal açıyor.
- [ ] Teknik Mod default kapalı.

## Etiket Studio

- [ ] İsim/Tarih/Not live update çalışıyor.
- [ ] Drag x/y değiştiriyor.
- [ ] Corner resize width/height/font_size değiştiriyor.
- [ ] Side resize width/height değiştiriyor.
- [ ] Keyboard movement çalışıyor.
- [ ] Zoom modlarında interaction çalışıyor.
- [ ] PDF/PNG son state ile oluşuyor.
- [ ] PDF/PNG canvas ile aynı.

## Queue

- [ ] Yazdırma sırasına eklenen path doğru.
- [ ] Native popup yerine uygun web modal çıkıyor.
- [ ] Devam Et çalışıyor.
- [ ] Yazdırma Sırasına Git çalışıyor.
- [ ] Duplicate engeli korunuyor.

## Komutlar

- [ ] `node --check src\webui\app.js`
- [ ] `.venv\Scripts\python.exe -m pytest`
- [ ] Kalite kapısı gerekli ise çalıştırıldı.
- [ ] Screenshot alındı.

## Product Builder Final Soruları

- [ ] Normal kullanıcı bu akışı teknik bilgi olmadan kullanabilir mi?
- [ ] Etiket grafiği, yazı okunurluğu ve güvenli alan korunuyor mu?
- [ ] Canvas'ta görünen sonuç output/queue tarafına aynı taşınıyor mu?
- [ ] Yeni risk veya P0/P1 regresyon ihtimali kaldı mı?

## Final Gerçek Kullanıcı Testi

- [ ] Tüm geliştirmeler bittikten sonra ana sayfalar gerçek kullanıcı gibi gezildi mi?
- [ ] Etiket Modelleri, Etiket Studio, Toplu Etiket, Yazdırma Sırası ve Etiket Çıktıları gerçek click ile doğrulandı mı?
- [ ] Etiket Studio’da mouse drag, corner resize, side resize ve keyboard hareketleri gerçek state değişimiyle doğrulandı mı?
- [ ] PDF/PNG son canvas state ile aynı mı?
- [ ] Queue doğru ve doğrulanmış dosyayı mı aldı?
- [ ] Screenshotlar insan gözüyle incelendi mi?
- [ ] Rapor PASSED dese bile kullanıcı deneyimi bozuk görünen bir alan kaldı mı?
