# Teknik Bakım Notları

## Persistence Dosyaları

Bakımı yapılan ana JSON kaynakları:

- `data/name_cut_queue.json`
- `data/name_cut_transfer_history.json`
- `data/name_cut_export_history.json`
- `data/print_queue.json`
- `data/production_audit_log.json`
- `data/printer_profiles.json`
- Trendyol local cache ve mapping dosyaları
- Etiket Studio session/output kayıtları varsa ilgili data dosyaları

## Gate Komutları

Release öncesi ana komut:

```powershell
python scripts/production_final_regression_release_phase27_gate.py
```

Hızlı sağlık kontrolü:

```powershell
npm run test
```

Frontend syntax:

```powershell
node --check src/webui/app.js
```

## Backup / Restore

Yedek klasörü:

```text
backups/YYYY-MM-DD/ceyizhome_lab_backup_<timestamp>/
```

Her backup manifest ve checksum özeti içermelidir. Restore öncesinde dry-run ve snapshot zorunludur.

## Audit

Audit dosyası:

```text
data/production_audit_log.json
```

Yeni operasyonlar için event tipi, source/source_label, status, severity ve metadata alanları doldurulmalıdır. Secret veya API key audit/log içine yazılmamalıdır.

## Güvenlik Guard'ları

Riskli aksiyonlar `live_integration_guard` mantığı altında kalmalıdır:

- Trendyol canlı statü
- kargo etiketi
- fatura
- direct print
- lazer gönderim
- RDWorks aç/gönder

Default davranış disabled/dry-run olmalıdır.
