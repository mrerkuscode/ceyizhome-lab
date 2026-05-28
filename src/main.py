from __future__ import annotations

import argparse
import traceback
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from config_loader import ConfigError, load_settings, print_startup_summary
from excel_reader import read_orders_excel
from file_manager import create_report_folders, create_run_folders
from intelligence.material_efficiency_analyzer import analyze_material_efficiency
from intelligence.production_analyzer import analyze_orders
from intelligence.recommendation_engine import build_recommendations
from intelligence.reporting import write_intelligence_reports
from intelligence.review_reason_generator import build_review_reasons
from intelligence.smart_warnings import build_smart_warnings
from label_designer.label_service import render_labels_from_excel
from laser_nesting import validate_connected_cut_safety
from laser_service import generate_laser_jobs
from legacy_converter import convert_legacy_excel
from models import (
    BOTH,
    LASER_CUT,
    LASER_ENGRAVE,
    NONE,
    PRINT,
    AppSettings,
    Order,
    TEMPLATE_MISSING,
    TEMPLATE_NEEDS_REVIEW,
    ValidationIssue,
)
from print_service import find_print_template, generate_print_jobs
from report_writer import write_errors_report, write_summary_report
from template_writer import create_demo_orders, create_production_template
from validators import validate_and_build_orders


@dataclass(frozen=True)
class RunSummary:
    total_orders: int
    valid_orders: int
    error_count: int
    print_jobs: int
    laser_engrave_jobs: int
    laser_cut_jobs: int
    both_jobs: int
    none_jobs: int
    output_folder: Path
    reports_folder: Path
    dry_run: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Yerel üretim otomasyon MVP aracı.")
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Ayar dosyası yolu.",
    )
    parser.add_argument(
        "--excel",
        "--input",
        dest="excel",
        default=None,
        help="Excel sipariş dosyası yolu. Boş bırakılırsa settings.yaml kullanılır.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sadece kontrol yapar; üretim dosyası oluşturmaz.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Çıktı tarihi. Örnek: 2026-04-27",
    )
    parser.add_argument(
        "--create-template",
        action="store_true",
        help="Temiz üretim Excel şablonunu input/cyzella_production_template.xlsx olarak oluştur.",
    )
    parser.add_argument(
        "--create-demo",
        action="store_true",
        help="Örnek verili demo Excel dosyasını input/demo_siparisler.xlsx olarak oluştur.",
    )
    parser.add_argument(
        "--convert-legacy-excel",
        action="store_true",
        help="Eski Cyzella Excel dosyasını temiz üretim formatına dönüştür.",
    )
    parser.add_argument(
        "--render-labels",
        action="store_true",
        help="Cyzella Label Designer ile PDF/PNG etiket çıktıları oluştur.",
    )
    return parser.parse_args()


def run_production_flow(settings: AppSettings, input_excel: Path, run_date: date, dry_run: bool) -> int:
    print(f"Kullanılan Excel: {input_excel}")
    print("Sipariş dosyası okunuyor...")
    dataframe = read_orders_excel(input_excel)
    valid_orders, issues = validate_and_build_orders(dataframe, settings)

    if dry_run:
        run_dir, reports_dir, _logs_dir = create_report_folders(
            settings.output_dir,
            run_date,
            settings.app.output_date_format,
        )
        issues.extend(_collect_dry_run_issues(valid_orders, settings))
        print("")
        print("Dry-run modu: üretim dosyası oluşturulmadı.")
    else:
        paths = create_run_folders(settings.output_dir, run_date, settings.app.output_date_format)
        run_dir = paths.run_dir
        reports_dir = paths.reports_dir
        print_orders = [order for order in valid_orders if order.process_type in {PRINT, BOTH}]
        _, print_issues = generate_print_jobs(print_orders, run_dir, settings)
        issues.extend(print_issues)

        laser_orders = [
            order
            for order in valid_orders
            if order.process_type in {LASER_ENGRAVE, LASER_CUT, BOTH}
        ]
        _, laser_issues = generate_laser_jobs(laser_orders, run_dir, settings)
        issues.extend(laser_issues)

    _write_reports(settings, dataframe, valid_orders, issues, run_dir, reports_dir)
    summary = _build_summary(
        total_orders=len(dataframe),
        valid_orders=valid_orders,
        issues=issues,
        output_folder=run_dir,
        reports_folder=reports_dir,
        dry_run=dry_run,
    )
    _print_summary(summary, settings)
    return 0


def run_legacy_conversion(settings: AppSettings, input_excel: Path, run_date: date) -> int:
    run_dir, _reports_dir, _logs_dir = create_report_folders(
        settings.output_dir,
        run_date,
        settings.app.output_date_format,
    )
    converted_dir = run_dir / "converted"

    print(f"Kullanılan eski Excel: {input_excel}")
    print("Eski Excel temiz üretim formatına dönüştürülüyor...")
    result = convert_legacy_excel(input_excel, converted_dir)

    print("")
    print("Legacy Excel dönüştürme tamamlandı.")
    print(f"- Dönüştürülen satır: {result.converted_rows}")
    print(f"- Uyarı/inceleme kaydı: {result.warning_rows}")
    print(f"- Temiz Excel: {result.clean_excel_path}")
    print(f"- Normalized CSV: {result.normalized_csv_path}")
    print(f"- Uyarı raporu: {result.warnings_csv_path}")
    print("")
    print("Güvenlik: Bu komut üretim dosyası oluşturmaz, yazdırma yapmaz, lazer başlatmaz.")
    print("Lütfen cyzella_clean_orders.xlsx dosyasını üretime almadan önce kontrol edin.")
    return 0


def run_label_rendering(settings: AppSettings, input_excel: Path, run_date: date) -> int:
    if settings.print.mode != "label_designer":
        print("Etiket tasarım modu kapalı. Ayarlardan print.mode değerini label_designer yapın.")
        print("Güvenlik: CorelDRAW açılmadı, yazıcı çalışmadı, yalnızca bilgilendirme yapıldı.")
        return 0

    print(f"Kullanılan Excel: {input_excel}")
    print("Cyzella Label Designer PDF/PNG etiket çıktıları hazırlanıyor...")
    result = render_labels_from_excel(settings, input_excel, run_date)
    ok_count = sum(1 for row in result.rows if row.get("status") == "OK")
    error_count = sum(1 for row in result.rows if row.get("status") != "OK")

    print("")
    print("Etiket render işlemi tamamlandı.")
    print(f"- Başarılı etiket: {ok_count}")
    print(f"- Hata/uyarı: {error_count}")
    print("- Raporlar:")
    for path in result.report_paths:
        print(f"  {path}")
    print("")
    print("Güvenlik: CorelDRAW açılmadı, yazdırma yapılmadı, yalnızca PDF/PNG dosyaları üretildi.")
    return 0


def _collect_dry_run_issues(orders: list[Order], settings: AppSettings) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for order in orders:
        if order.process_type in {PRINT, BOTH}:
            match = find_print_template(
                settings.print_templates_dir,
                order.model_no,
                order.template_no,
                order.label_variant,
            )
            if match.status in {TEMPLATE_MISSING, TEMPLATE_NEEDS_REVIEW}:
                issues.append(
                    ValidationIssue(
                        row_number=order.row_number,
                        order_no=order.order_no,
                        field="print_template",
                        message=_print_template_message(order, match.status),
                    )
                )

        if order.process_type in {LASER_CUT, BOTH}:
            connected_error = validate_connected_cut_safety(order, settings)
            if connected_error is not None:
                _status, _parts, warning = connected_error
                issues.append(
                    ValidationIssue(
                        row_number=order.row_number,
                        order_no=order.order_no,
                        field="laser_text",
                        message=warning,
                    )
                )

    return issues


def _write_reports(
    settings: AppSettings,
    dataframe,
    valid_orders: list[Order],
    issues: list[ValidationIssue],
    run_dir: Path,
    reports_dir: Path,
) -> None:
    if settings.reports.generate_summary_report:
        write_summary_report(
            reports_dir / "summary_report.csv",
            total_rows=len(dataframe),
            valid_orders=valid_orders,
            issues=issues,
        )
    if settings.reports.generate_errors_report:
        write_errors_report(reports_dir / "errors_report.csv", issues)

    intelligence_findings = analyze_orders(dataframe, valid_orders, settings)
    recommendations = build_recommendations(valid_orders, settings)
    smart_warnings = build_smart_warnings(valid_orders, issues, intelligence_findings + recommendations)
    review_reasons = build_review_reasons(issues, smart_warnings, recommendations)
    material_efficiency = analyze_material_efficiency(
        run_dir,
        settings.laser.plate_width_mm,
        settings.laser.plate_height_mm,
    )
    write_intelligence_reports(
        reports_dir=reports_dir,
        warnings=smart_warnings,
        review_reasons=review_reasons,
        material_efficiency_rows=material_efficiency,
        valid_orders=valid_orders,
        issues=issues,
    )


def _build_summary(
    total_orders: int,
    valid_orders: list[Order],
    issues: list[ValidationIssue],
    output_folder: Path,
    reports_folder: Path,
    dry_run: bool,
) -> RunSummary:
    counts = Counter(order.process_type for order in valid_orders)
    return RunSummary(
        total_orders=total_orders,
        valid_orders=len(valid_orders),
        error_count=len(issues),
        print_jobs=counts.get(PRINT, 0),
        laser_engrave_jobs=counts.get(LASER_ENGRAVE, 0),
        laser_cut_jobs=counts.get(LASER_CUT, 0),
        both_jobs=counts.get(BOTH, 0),
        none_jobs=counts.get(NONE, 0),
        output_folder=output_folder,
        reports_folder=reports_folder,
        dry_run=dry_run,
    )


def _print_summary(summary: RunSummary, settings: AppSettings) -> None:
    print("")
    print("İşlem özeti")
    print(f"- Toplam sipariş: {summary.total_orders}")
    print(f"- Geçerli sipariş: {summary.valid_orders}")
    print(f"- Hata/inceleme kaydı: {summary.error_count}")
    print(f"- Print jobs: {summary.print_jobs}")
    print(f"- Laser engrave jobs: {summary.laser_engrave_jobs}")
    print(f"- Laser cut jobs: {summary.laser_cut_jobs}")
    print(f"- Both jobs: {summary.both_jobs}")
    print(f"- Output klasörü: {summary.output_folder}")

    if summary.error_count:
        if settings.reports.generate_errors_report:
            print("")
            print("Hata raporu oluşturuldu:")
            print(f"- {summary.reports_folder / 'errors_report.csv'}")
            print("Lütfen üretime geçmeden önce bu raporu kontrol edin.")
        else:
            print("")
            print("Hata var, ancak settings.yaml içinde errors_report kapalı.")

    print("")
    if summary.dry_run:
        print(f"Gerçek çalıştırmada print dosyaları burada hazırlanır: {summary.output_folder / 'print'}")
        print(f"Gerçek çalıştırmada lazer dosyaları burada hazırlanır: {summary.output_folder / 'laser'}")
        print("Güvenlik: Dry-run çalıştı; print/lazer üretim dosyası oluşturulmadı.")
    else:
        print("Güvenlik: Yazdırma yapılmadı, RDWorks açılmadı, lazer başlatılmadı.")


def _print_template_message(order: Order, status: str) -> str:
    if status == TEMPLATE_NEEDS_REVIEW:
        return (
            "Birden fazla print şablonu eşleşti, kontrol gerekli: "
            f"model_no {order.model_no}, template_no {order.template_no}, "
            f"label_variant {order.label_variant}"
        )
    return (
        "Missing print template for "
        f"model_no {order.model_no}, template_no {order.template_no}, "
        f"label_variant {order.label_variant}"
    )


def _parse_run_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Tarih formatı geçersiz. Örnek: 2026-04-27") from exc


def _resolve_project_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root / path


def _write_exception_log(project_root: Path, run_date_text: str, exc: BaseException) -> Path:
    try:
        run_date = _parse_run_date(run_date_text)
        log_dir = project_root / "output" / run_date.isoformat() / "logs"
    except ValueError:
        log_dir = project_root / "output" / date.today().isoformat() / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    log_path.write_text(
        "".join(
            [
                "Production Bot developer error\n",
                f"Error type: {type(exc).__name__}\n",
                f"Error message: {exc}\n\n",
                traceback.format_exc(),
            ]
        ),
        encoding="utf-8",
    )
    return log_path


def cli() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    try:
        config_path = _resolve_project_path(project_root, args.config)
        settings = load_settings(config_path)
        run_date = _parse_run_date(args.date)
        print_startup_summary(settings)

        if args.create_template:
            template_path = create_production_template(settings.project_root / "input" / "cyzella_production_template.xlsx")
            print(f"Boş üretim Excel şablonu oluşturuldu: {template_path}")
            return 0

        if args.create_demo:
            demo_path = create_demo_orders(settings.project_root / "input" / "demo_siparisler.xlsx")
            print(f"Demo sipariş Excel dosyası oluşturuldu: {demo_path}")
            return 0

        if args.convert_legacy_excel:
            input_excel = _resolve_project_path(settings.project_root, args.excel) if args.excel else settings.input_excel
            return run_legacy_conversion(settings, input_excel, run_date)

        input_excel = _resolve_project_path(settings.project_root, args.excel) if args.excel else settings.input_excel
        if args.render_labels:
            return run_label_rendering(settings, input_excel, run_date)

        return run_production_flow(settings, input_excel, run_date, dry_run=args.dry_run)
    except ConfigError as exc:
        print("")
        print("Ayar hatası:")
        print(f"- {exc}")
        print("")
        print("Lütfen config/settings.yaml dosyasını kontrol edin.")
        return 1
    except FileNotFoundError as exc:
        print("")
        print("Dosya bulunamadı:")
        print(f"- {exc}")
        print("")
        print("Lütfen Excel dosyasının doğru klasörde olduğundan emin olun.")
        return 1
    except PermissionError as exc:
        print("")
        print("Dosya kullanılıyor:")
        print(f"- {exc}")
        print("")
        print("Excel dosyası açık olabilir. Lütfen dosyayı kapatıp tekrar deneyin.")
        return 1
    except ValueError as exc:
        print("")
        print("Giriş hatası:")
        print(f"- {exc}")
        print("")
        print("Lütfen tarih, sayı veya ayar değerlerini kontrol edin.")
        return 1
    except Exception as exc:
        log_path = _write_exception_log(project_root, args.date, exc)
        print("")
        print("Beklenmeyen teknik hata oluştu.")
        print("Program güvenli şekilde durduruldu; yazdırma veya lazer başlatma yapılmadı.")
        print(f"Teknik log dosyası: {log_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
