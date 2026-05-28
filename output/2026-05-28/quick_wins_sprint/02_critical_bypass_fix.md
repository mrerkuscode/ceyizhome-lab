# 02 — Kritik Bypass Düzeltmesi: `_initial_verification_status`

## Bağlam — İrem/Ümit krizinin kökü

Bu fonksiyon, Trendyol'dan gelen siparişlerin "doğrulama durumunu" hesaplıyordu. Bug: AI cloud confidence ≥0.85 + safe source + cloud_ai_ready + not needs_user_review → otomatik `VERIFICATION_READY` döner. Akış:

1. `_suggestion_from_line` (`trendyol_api.py:1853`) yeni satır oluşturur
2. `_initial_verification_status` bypass yolunu döndürür → `VERIFICATION_READY`
3. Aynı fonksiyon (line 1874): `user_verified = (verification_status == VERIFICATION_READY)` → **True**
4. (line 1916-1917): `verified_at = now`, `verified_by = "cloud_ai"`
5. `_is_verified_ready()` → True → satır üretime hazır olarak işaretlenir
6. **Operatör onay butonuna basmadı bile.**

CLAUDE.md ihlali doğrudan: "Operatör onayı zorunlu, AI önerisi onay yerine geçmez."

## Önce — eski davranış (trendyol_api.py:1933-1953)

```python
def _initial_verification_status(mapping_found, production_type, extracted, has_question):
    if not has_question:
        return VERIFICATION_WAITING_EVIDENCE
    if not mapping_found or production_type in {"review", "none", ""}:
        return VERIFICATION_USER_REVIEW
    sources = extracted.get("field_sources") if isinstance(extracted.get("field_sources"), dict) else {}
    label_source = sources.get("label_text")
    cut_source = sources.get("name_cut_text")
    safe_source = label_source in {"question_text", "answer_text"} or cut_source in {"question_text", "answer_text"}
    evidence = set(extracted.get("source_evidence") or [])
    cloud_ai_ready = bool(evidence.intersection({"cloud_ai_extract", "cloud_ai_cache"}))
    if (
        float(extracted.get("confidence") or 0) >= DEFAULT_CONFIDENCE_THRESHOLD
        and safe_source
        and cloud_ai_ready
        and not bool(extracted.get("needs_user_review"))
    ):
        return VERIFICATION_READY    # <-- BYPASS
    if float(extracted.get("confidence") or 0) < 0.7:
        return VERIFICATION_USER_REVIEW
    return VERIFICATION_WAITING_APPROVAL
```

## Sonra — yeni davranış

```python
def _initial_verification_status(mapping_found, production_type, extracted, has_question):
    # Operator approval is mandatory (CLAUDE.md). New rows imported from
    # Trendyol must NEVER auto-advance to VERIFICATION_READY based on AI
    # confidence alone — that was the İrem/Ümit incident root cause
    # (high cloud-AI confidence silently set user_verified=True and sent
    # rows to production without operator review). The READY state is
    # reached ONLY via the explicit operator approval path in
    # set_suggestion_user_verified() (writes verified_by="local_user").
    if not has_question:
        return VERIFICATION_WAITING_EVIDENCE
    if not mapping_found or production_type in {"review", "none", ""}:
        return VERIFICATION_USER_REVIEW
    if float(extracted.get("confidence") or 0) < 0.7:
        return VERIFICATION_USER_REVIEW
    return VERIFICATION_WAITING_APPROVAL
```

Bu fonksiyon artık **hiçbir koşulda** `VERIFICATION_READY` döndürmez. Tek meşru READY yolu: operatör onay butonu → `set_suggestion_user_verified()` → `verified_by="local_user"`.

## Etki zinciri

`_suggestion_from_line` artık her zaman:
- `verification_status` ∈ {WAITING_EVIDENCE, USER_REVIEW, WAITING_APPROVAL}
- `status = "review"` (READY değil)
- `user_verified = False`
- `verified_at = ""`
- `verified_by = ""`

`_is_verified_ready` (line 1956) yeni satırlar için **her zaman False** döner. readyForCut downstream False. CLAUDE.md uyumlu.

## Test sonuçları

```
Test 1 (high-confidence AI: 0.95, cloud_ai, safe source):
  öncesi: VERIFICATION_READY (BYPASS)
  sonrası: VERIFICATION_WAITING_APPROVAL ✅

Test 2 (no question):                 VERIFICATION_WAITING_EVIDENCE ✅
Test 3 (no mapping):                  VERIFICATION_USER_REVIEW ✅
Test 4 (low confidence: 0.5):         VERIFICATION_USER_REVIEW ✅
Test 5 (medium confidence: 0.78):     VERIFICATION_WAITING_APPROVAL ✅
```

## Regresyon — mevcut operator-approved kayıtlar

`data/trendyol_production_suggestions.json` içinde mevcut satırlar:
- `Ayşe & Mehmet` → `verification_status=uretime_hazir`, `user_verified=True`
- `_is_verified_ready()` halen **True** döner (manuel set edilmiş alan)
- İrem/Ümit/Ahmet pattern'i de aynı şekilde korunur — geçmiş veriler dokunulmaz

Görsel:
```
Mevcut READY satır: 1
_is_verified_ready için True dönen: 1  → regresyon TEMİZ ✅
```

## Backup

`output/2026-05-28/quick_wins_sprint/backups/trendyol_api.py.bak`

## Diff özeti

- Net 9 satır kod silindi (bypass koşulu + ilgili intermediate değişkenler)
- 8 satır yorum eklendi (neden + tarihçe)
- Davranış değişikliği: yüksek-güvenli AI önerileri için tek satır return değiştirildi
