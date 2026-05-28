# 02 — Ölü Kod / Eski Deneme Kalıntıları

**Yöntem:** Statik grep + audit raporu çapraz kontrolü.

## Dosya düzeyinde
| Dosya | Durum | Not |
|---|---|---|
| `src/legacy_converter.py` | Eski (adı "legacy") | İncelenmesi gerekiyor — kullanım var mı, kullanılmıyorsa kaldırılabilir |
| `src/desktop/main_window.py` + `src/desktop/web_main_window.py` | Çift | İkisi paralel mı (legacy + web), birisi seçilebilir mi? |

## Default-OFF (mevcut, korunan, kullanılmayan) algoritmalar (combined_production_api.py)
İsim kesim için 6 stratejik algoritma yazıldı; en son `targeted_stroke_weld` aktif, diğerleri default OFF (geri-alma için tutuldu):
- `_initial_letter_connection_reinforcement_contours` (~3402) — bridge stratejisi, default OFF (bowtie sebebi)
- `_designer_letter_flow_bridge_*` (~3523/3626) — bridge, default OFF
- `_welded_baseline_support_contours` (~3000+) — support_line bar, default OFF (opt-in)
- contour-only 0.65 strategy denendi → blob → rafa
- uniform overlap (letter_spacing tightening) denendi → mush → rafa

**Karar:** Bu kod parçaları temizlenmemeli (henüz). Leyla'nın DXF kütüphane sistemi geçişi sonrası, `targeted_weld` da dahil tüm jeneratif algoritmalar fallback'e çekilir, sonra kademeli sadeleştirme yapılabilir.

## "AI" yanıltıcı isimlendirme (sahte AI iddiası, audit Faz 6'da raporlandı)
İnternal `ai_quality*` keys + `_ai_laser_quality_*` fonksiyonları + frontend "AI Guided" etiketleri — gerçekte deterministik (`aiFinalPathGenerated:False`, kanıtlı). Backend display string'leri düzeltildi (önceki turlar); **internal keys + frontend labels koordineli rename bekliyor** (UI kırma riski olmadan).

## Çift fonksiyon / sürüm
- `_targeted_stroke_weld_contours` ve eski bridge fn'leri — aynı amacı farklı yöntemlerle yapar; bridge'ler default OFF.
- `_outline_contours_for_item` `path_role` parametresi (preview/cut) — preview ile cut'ı ayırıyor; meşru.
- Kanıt-eşleştirme: bu turdaki audit'te bazı `linkedIds` boş atama (BUG-03 10_kanit_eslesme:64 — ölü kod bloğu).

## "Bilinen takip" notları (audit'ten — kod kalıntısı değil ama temizlik kalemi)
- Welded support_line iken export'ta hâlâ AYRI dekoratif `<line>` çiziliyor (~7057/7083/7155/7190) — çift çizgi (audit 17_veri_bakimi). Düzeltilebilir, düşük öncelik.
- `_pair_kerning_signature` / `_golden_glyph_scale_signature` JSON-encoded parametreler — kullanım izi kontrol edilmeli.

## TODO/FIXME tarama sonucu
src/ altında **TODO/FIXME/HACK/DEPRECATED match: 0** (yorum işaretçileri kullanılmamış — kod yorumla işaretlenmemiş; iyi bir disiplin işareti).

## Öneri
🔴 **SİL adayları (önce kullanım kontrolü):**
- `legacy_converter.py` — import edilmiyor görünüyor; CSV/regex import; geçmiş veri import için tutulmuş olabilir. → Önce: import grep yap, kullanım var mı.
- `desktop/main_window.py` — `web_main_window.py` ile çift; kullanım yolu kontrol edilmeli.

🟡 **DÜZELT (rename / cleanup):**
- "AI" yanıltıcı isimlendirme → "deterministic" / "algorithm" rename (koordineli frontend+backend, ~4 saat).
- Bridge/support_line/contour eski algoritmalar — DXF kütüphane sistemine geçince temizle (2-3 saat).

🟢 **DOKUNMA:** Default-OFF stratejik algoritmalar (geri-alma için bilinçli korundu).
