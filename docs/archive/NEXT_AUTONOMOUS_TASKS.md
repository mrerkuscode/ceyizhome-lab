# Next Autonomous Tasks

Updated: 2026-05-17

## Do Next Without Waiting

1. **User Trendyol acceptance test**
   - Trendyol > Urun Eslestirme tabinda arama/filtre ile gercek urunleri bulun.
   - Etiket veya Etiket + Isim Kesim secilen her urunde model secin; model olmadan onay bilincli olarak engellenir.
   - Kaydet ve Siparise Don ile Siparisler tabina gecin.
   - Soru kaniti gorunen bir satirda soru metnini okuyun, `Bu metinden alanlari kullan`, `Onayla ve Uretime Hazir Yap`, ardindan `Uretime Aktar` akisini deneyin.

2. **Real user visual QA pass**
   - Open Home, Etiket Modelleri, Etiket Studio, Toplu Etiket, Yazdirma Sirasi, Etiket Ciktilari, Trendyol, Siparisler and RDWorks/Isim Kesim.
   - Confirm there is no flicker, disappearing content, broken preview or cut-off action footer.
   - If a visual issue appears, fix it before adding features.

3. **Only if user test finds an issue**
   - Fix any real UI issue found in Trendyol product mapping, question evidence, Studio handoff or queue output.
   - Keep marketplace credentials and old `mucoxai1` project untouched.

## Already Verified

- Trendyol question evidence resilience: read-only WaitingForAnswer + Answered sync, sanitized service-unavailable status, UI evidence filters.
- Live Trendyol safe blocking when question evidence is unavailable.
- Studio layout stability and Corel editor interactions.
- Studio undo/redo.
- Label model catalog premium flow.
- Bulk Excel gallery, 100 row fixture, edit modal, manifest and queue.
- Outputs customer gallery and technical archive separation.
- Print queue preview, print modal, clear queue confirmation and status transitions.
- Clean customer demo flow.
- Workshop operations dashboard and queue detail.
- Customer order creation, Studio handoff and queue output.
- RDWorks name-cut DXF/SVG/PDF/PNG/manifest export.
- Combined Excel label + name-cut split.
- New model wizard.
- User onboarding and technical visibility.
- Design system consistency.
- Release package.
- Trendyol order-to-production flow.
- Trendyol product mapping review workflow.
- Trendyol live mapping readiness.
- Trendyol final operator handoff: searchable/filterable catalog suggestions, no label mapping approval without model, save-and-return action.
- Real production quality gate.
- Final acceptance gate.

## Safety Rules To Keep

- Do not open RDWorks.
- Do not start laser.
- Do not enable direct print.
- Do not silently start printer.
- Do not open CorelDRAW or Illustrator.
- Do not modify source AI/CDR files.
- Do not modify `C:\Users\Pc\Desktop\mucoxai1`.
- Do not copy or print marketplace secrets.
