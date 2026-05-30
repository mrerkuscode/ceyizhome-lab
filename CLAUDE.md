# Claude — CeyizHome Lab Rehberi

> Bu dosya HER Claude sohbetinin ilk okudugu dosyadir.

## SEN KIMSIN?

Ilk once kim oldugunu belirle:

- Claude Code (Terminal): Lokal kod yazma, test, git
- Claude Chrome (Tarayici): Gorsel inceleme, GitHub edit, PR inceleme/merge, canli localhost testi
- Web Claude (claude.ai): Plan, prompt, mockup

## ILK ADIMLARIN

1. Bu dosyayi oku (CLAUDE.md) — SEN BURADASIN
2. PROJECT_CONTEXT.md → genel proje bilgisi
3. ACTIVE_SPRINT.md → su an ne yapiliyor
4. FORBIDDEN.md → yasaklari kontrol et

## ONEMLI DOSYALAR

| Dosya | Ne icin |
|-------|---------|
| CLAUDE.md | Bu dosya - ana giris |
| PROJECT_CONTEXT.md | Proje hakkinda her sey |
| WORKFLOW.md | Multi-Claude pattern |
| FORBIDDEN.md | Yasak alanlar |
| ACTIVE_SPRINT.md | Aktif sprint durumu |
| docs/decisions/ | Karar log (ADR) |

## HIZLI KURALLAR

- Yeni framework ekleme (Bootstrap, Tailwind, React, FastAPI vb.) YOK
- Master flag kapali kodlara dokunma (AI Glyph, Internal Corel) YOK
- Mevcut testleri koru, yeni test ekle
- Her is icin ayri branch + commit + PR
- Turkce karakter UTF-8 (BOM YOK)
- git push --force / git reset --hard YASAK

## SON DURUM

- Branch: main
- MVP: ~%99
- Test: 68/68 PASS (CI #19 dahil)
- Son commit: 11ee135 (Isim Kesim tabla ici duzenleme + karakter kaybi fix)

---

Detay icin → PROJECT_CONTEXT.md
