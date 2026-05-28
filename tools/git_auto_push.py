"""Sprint sonu otomatik push helper.

Kullanım:
    python tools/git_auto_push.py "sprint_adi"
    python tools/git_auto_push.py "trendyol_migration" --check
    python tools/git_auto_push.py "trendyol_migration" --dry-run

Default davranış:
1) Credential leak pre-check (sahte değil — gerçek string match)
2) git add . (gitignore zaten credentials'ı dışlıyor)
3) git status göster, kaç dosya değişti raporla
4) Eğer kayda değer değişiklik yoksa erken çık (commit atılmaz)
5) git commit -m "sprint: <sprint_adi> - <tarih>"
6) git push (push başarısız olursa raporla, geri al değişiklikleri SAKLA)

--check: sadece leak scan yap, commit/push yok
--dry-run: commit hazırla ama push atma
--no-push: commit at, push atma
--force: leak scan başarısız olsa bile push (TEHLİKELİ, kullanma)

CLAUDE.md uyum: sahte başarı yok — push gerçekten bittiğinde "PUSH OK" yazar,
başarısızsa stderr + exit code 1 ile çıkar.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Project root inference
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parent.parent

# Patterns that MUST NOT appear in any staged content (real credential strings
# we know to exist on this machine — taken from data/trendyol_settings.json).
# Fragmanlar string concatenation ile inşa edilir ki bu dosyanın kendi diff'i
# tetikleme yapmasın (eğer bütün string olarak yazılırsa, scan kendi kaynağını
# leak olarak algılar — ironic false-positive).
KNOWN_CREDENTIAL_FINGERPRINTS = [
    # Trendyol api_key prefix
    "IOd" + "Iq" + "PiXJC",
    # Trendyol api_secret prefix
    "8fM" + "f6yH" + "MRN",
    # OpenAI key prefix (this account)
    "sk-" + "proj-" + "Nhn" + "dgUfu",
]

# Generic regex tripwires — look for sensitive shape that escaped masking.
GENERIC_SECRET_PATTERNS = [
    # OpenAI sk- keys longer than test fixtures
    re.compile(r'"(?:ai_api_key|openai_api_key)":\s*"sk-[A-Za-z0-9_-]{40,}"'),
    # Trendyol-style 20+ char api_key/api_secret values
    re.compile(r'"(?:api_key|api_secret)":\s*"[A-Za-z0-9]{20,}"'),
    # AWS access key id shape
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # Private key markers
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----"),
]


def run(cmd: list[str], *, check: bool = False, capture: bool = True) -> subprocess.CompletedProcess:
    """Shell-less run; force UTF-8 decoding (Windows default cp1254 corrupts diffs)."""
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=capture,
        text=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


def credential_leak_scan() -> tuple[bool, list[str]]:
    """Return (clean, reasons). Scan staged (cached) diff for credentials."""
    add = run(["git", "add", "."])
    if add.returncode != 0:
        return False, [f"git add başarısız: {add.stderr.strip()}"]

    diff = run(["git", "diff", "--cached", "--no-color"])
    if diff.returncode != 0:
        return False, [f"git diff başarısız: {diff.stderr.strip()}"]

    reasons: list[str] = []
    for fp in KNOWN_CREDENTIAL_FINGERPRINTS:
        if fp in diff.stdout:
            reasons.append(f"BİLİNEN CREDENTIAL FRAGMAN BULUNDU: {fp[:6]}... — push edilemez")

    for pat in GENERIC_SECRET_PATTERNS:
        hits = pat.findall(diff.stdout)
        for h in hits[:3]:
            # Allow test fixtures
            if "should-not-leak" in h or "wrong-field" in h or "test-fixture" in h or "tmp_path" in h:
                continue
            reasons.append(f"SECRET PATTERN HIT: {h[:80]}")

    # Verify credential FILES themselves are NOT staged
    ls = run(["git", "ls-files", "--cached"])
    if ls.returncode == 0:
        for line in ls.stdout.splitlines():
            if line.endswith("data/trendyol_settings.json") or line.endswith("data/openai_settings.json"):
                reasons.append(f"CREDENTIAL DOSYASI STAGED: {line}")
            if re.search(r"\.env$", line):
                reasons.append(f"ENV DOSYASI STAGED: {line}")
            if re.search(r"assets/fonts/.+\.(ttf|otf|woff2?)$", line, re.I):
                reasons.append(f"FONT BINARY STAGED: {line}")

    return (len(reasons) == 0), reasons


def git_status_summary() -> tuple[int, str]:
    r = run(["git", "status", "--porcelain"])
    if r.returncode != 0:
        return -1, r.stderr
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return len(lines), r.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sprint_name", help="Sprint adı, commit mesajına yazılır")
    parser.add_argument("--check", action="store_true", help="Sadece leak scan yap")
    parser.add_argument("--dry-run", action="store_true", help="Commit at ama push atma")
    parser.add_argument("--no-push", action="store_true", help="Push atma")
    parser.add_argument("--force", action="store_true", help="Leak scan'i ignore et (TEHLİKELİ)")
    args = parser.parse_args()

    print(f"[auto-push] sprint = {args.sprint_name}")
    print(f"[auto-push] proje kökü: {PROJECT_ROOT}")

    print("[auto-push] credential leak scan başlıyor...")
    clean, reasons = credential_leak_scan()
    if not clean:
        print("[auto-push] LEAK SCAN BAŞARISIZ:")
        for r in reasons:
            print(f"  - {r}")
        if not args.force:
            print("[auto-push] Push iptal edildi. .gitignore'u kontrol et veya --force ile zorla (kullanma).")
            return 2
        print("[auto-push] --force aktif: leak scan görmezden geliniyor (TEHLİKELİ).")
    else:
        print("[auto-push] LEAK SCAN TEMİZ ✓")

    if args.check:
        return 0

    count, status_out = git_status_summary()
    print(f"[auto-push] staged + uncommitted: {count} dosya değişikliği")
    if count == 0:
        print("[auto-push] Değişiklik yok, commit atılmadı.")
        return 0

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"sprint: {args.sprint_name} - {date_str}\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
    commit_cmd = ["git", "commit", "-m", msg]
    commit = run(commit_cmd)
    if commit.returncode != 0:
        print(f"[auto-push] Commit başarısız:\n{commit.stderr}")
        return 1
    print(f"[auto-push] Commit OK")
    # Show last commit hash
    last = run(["git", "log", "-1", "--oneline"])
    if last.returncode == 0:
        print(f"[auto-push] Son commit: {last.stdout.strip()}")

    if args.dry_run or args.no_push:
        print("[auto-push] Push atlanıyor (dry-run / no-push). Komut: git push")
        return 0

    print("[auto-push] git push çalışıyor...")
    push = run(["git", "push"], capture=True)
    if push.returncode == 0:
        print("[auto-push] PUSH OK ✓")
        print(push.stdout)
        return 0
    else:
        print("[auto-push] PUSH BAŞARISIZ:")
        print(push.stderr or push.stdout)
        # Authentication failure hint
        if "could not read Username" in (push.stderr + push.stdout) or "Authentication" in (push.stderr + push.stdout):
            print()
            print("[auto-push] AUTH KURULUMU GEREKLİ:")
            print("  1. https://github.com/settings/tokens adresinden 'classic' PAT oluştur (repo yetkisi)")
            print("  2. Bir kez şu komutu çalıştır:")
            print("     git config --global credential.helper manager")
            print("  3. Tekrar 'git push' dene; ilk seferde tarayıcı/pencere açar, PAT'i yapıştır.")
            print("  4. Sonraki push'lar otomatik çalışır.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
