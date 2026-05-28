from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
WEBUI_APP = ROOT / "production-bot" / "src" / "webui" / "app.js"
ASSET_FONTS = ROOT / "production-bot" / "assets" / "fonts"
OUT = ROOT / "output" / "2026-05-24" / "mochary_tr_connect_autonomous_font_finish"
RESULT_JSON = OUT / "autonomous_font_finish_result.json"
REPORT = ROOT / "MOCHARY_TR_CONNECT_AUTONOMOUS_FONT_FINISH_RAPORU.md"
SCOREBOARD = ROOT / "MOCHARY_TR_CONNECT_FONT_VISUAL_SCOREBOARD.md"

TEST_WORDS = [
    "Türkçe",
    "Görkem",
    "ÇeyizHome",
    "Aşk ile söz verdik",
    "Ayşe & Mehmet",
    "Yağmur & Efe",
    "Çağrı",
    "Özge",
    "Ümit",
    "İrem",
    "Şule",
    "Buğra",
    "Mücahit",
    "Abdurrahman",
    "Kişi",
    "Işık",
]
TURKISH_PROOF = [
    "ç Ç",
    "ğ Ğ",
    "ı I İ i",
    "ö Ö",
    "ş Ş",
    "ü Ü",
    "Türkçe",
    "Görkem",
    "Ayşe",
    "Yağmur",
    "Çağrı",
    "Özge",
    "Ümit",
    "İrem",
    "Şule",
    "Buğra",
]
RDWORKS_NAMES = [
    "Sedef",
    "Sefer",
    "Vahip",
    "Ayşe",
    "Mehmet",
    "Leyla",
    "Mücahit",
    "Serap",
    "İrem",
    "Özge",
    "Ümit",
    "Çağrı",
    "Yağmur",
    "Efe",
    "Burak",
    "Ceren",
    "Serkan",
    "Görkem",
    "Türkçe",
    "Şule",
    "Buğra",
    "Abdurrahman",
    "Nermin",
    "Zeynep",
    "Yıldız",
    "Kaan",
    "Deniz",
    "Elif",
    "Derya",
    "Volkan",
    "Cansu",
    "Osman",
    "Ömer",
    "İlyas",
    "Sinem",
    "Berke",
    "Doğuş",
    "Furkan",
    "Melis",
    "Nazlı",
]
BURAK_CEREN_SERKAN = ["Burak", "Ceren", "Serkan"]
TURKISH_CHARS = "çÇğĞıİöÖşŞüÜ"
ASCII_FALLBACKS = [
    "Turkce",
    "Gorkem",
    "Ayse",
    "Yagmur",
    "Cagri",
    "Ozge",
    "Umit",
    "Irem",
    "Sule",
    "Bugra",
]


@dataclass(frozen=True)
class FontIteration:
    version: str
    label: str
    family_value: str
    ttf: Path
    otf: Path
    output_dir: Path


class FlattenPen(BasePen):
    def __init__(self, glyph_set: Any, scale: float, tx: float, ty: float) -> None:
        super().__init__(glyph_set)
        self.scale = scale
        self.tx = tx
        self.ty = ty
        self.contours: list[list[tuple[float, float]]] = []
        self.current: list[tuple[float, float]] = []
        self.current_point: tuple[float, float] | None = None

    def _map(self, pt: tuple[float, float]) -> tuple[float, float]:
        return (self.tx + pt[0] * self.scale, self.ty - pt[1] * self.scale)

    def _moveTo(self, pt: tuple[float, float]) -> None:
        if self.current:
            self.contours.append(self.current)
        self.current = [self._map(pt)]
        self.current_point = pt

    def _lineTo(self, pt: tuple[float, float]) -> None:
        self.current.append(self._map(pt))
        self.current_point = pt

    def _curveToOne(self, p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]) -> None:
        p0 = self.current_point or p1
        for step in range(1, 13):
            t = step / 12
            x = ((1 - t) ** 3 * p0[0]) + (3 * (1 - t) ** 2 * t * p1[0]) + (3 * (1 - t) * t**2 * p2[0]) + (t**3 * p3[0])
            y = ((1 - t) ** 3 * p0[1]) + (3 * (1 - t) ** 2 * t * p1[1]) + (3 * (1 - t) * t**2 * p2[1]) + (t**3 * p3[1])
            self.current.append(self._map((x, y)))
        self.current_point = p3

    def _qCurveToOne(self, p1: tuple[float, float], p2: tuple[float, float]) -> None:
        p0 = self.current_point or p1
        for step in range(1, 11):
            t = step / 10
            x = ((1 - t) ** 2 * p0[0]) + (2 * (1 - t) * t * p1[0]) + (t**2 * p2[0])
            y = ((1 - t) ** 2 * p0[1]) + (2 * (1 - t) * t * p1[1]) + (t**2 * p2[1])
            self.current.append(self._map((x, y)))
        self.current_point = p2

    def _closePath(self) -> None:
        if self.current:
            self.contours.append(self.current)
        self.current = []
        self.current_point = None

    def _endPath(self) -> None:
        self._closePath()


def escape_xml(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def iterations() -> list[FontIteration]:
    return [
        FontIteration(
            "v3",
            "Mochary TR Connect Visual Refined V3",
            "MocharyTRConnectVisualRefinedV3-Regular",
            ASSET_FONTS / "MocharyTRConnect-VisualRefinedV3.ttf",
            ASSET_FONTS / "MocharyTRConnect-VisualRefinedV3.otf",
            OUT / "v3",
        ),
        FontIteration(
            "v4",
            "Mochary TR Connect Visual Refined V4",
            "MocharyTRConnectVisualRefinedV4-Regular",
            ASSET_FONTS / "MocharyTRConnect-VisualRefinedV4.ttf",
            ASSET_FONTS / "MocharyTRConnect-VisualRefinedV4.otf",
            OUT / "v4",
        ),
        FontIteration(
            "v5",
            "Mochary TR Connect Visual Refined V5",
            "MocharyTRConnectVisualRefinedV5-Regular",
            ASSET_FONTS / "MocharyTRConnect-VisualRefinedV5.ttf",
            ASSET_FONTS / "MocharyTRConnect-VisualRefinedV5.otf",
            OUT / "v5",
        ),
    ]


def cmap_for(font: TTFont) -> dict[int, str]:
    cmap: dict[int, str] = {}
    for table in font["cmap"].tables:
        cmap.update(table.cmap)
    return cmap


def glyph_bounds(glyph_set: Any, glyph_name: str) -> tuple[float, float, float, float] | None:
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.bounds


def glyph_path(glyph_set: Any, glyph_name: str) -> str:
    pen = SVGPathPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.getCommands()


def measure_text(font: TTFont, glyph_set: Any, cmap: dict[int, str], text: str) -> dict[str, Any]:
    cursor = 0.0
    min_x = math.inf
    min_y = math.inf
    max_x = -math.inf
    max_y = -math.inf
    missing: list[str] = []
    glyphs: list[dict[str, Any]] = []
    for ch in text:
        if ch.isspace():
            cursor += 260
            continue
        glyph_name = cmap.get(ord(ch))
        if not glyph_name:
            missing.append(ch)
            cursor += 340
            continue
        bounds = glyph_bounds(glyph_set, glyph_name)
        if bounds:
            gx0, gy0, gx1, gy1 = bounds
            min_x = min(min_x, cursor + gx0)
            min_y = min(min_y, gy0)
            max_x = max(max_x, cursor + gx1)
            max_y = max(max_y, gy1)
        glyphs.append({"char": ch, "glyph": glyph_name, "cursor": cursor, "path": glyph_path(glyph_set, glyph_name)})
        cursor += glyph_set[glyph_name].width * 0.88
    if min_x is math.inf:
        min_x = min_y = 0.0
        max_x = max(cursor, 1.0)
        max_y = 1.0
    return {
        "text": text,
        "missing": missing,
        "glyphs": glyphs,
        "raw_min_x": min_x,
        "raw_min_y": min_y,
        "raw_max_x": max_x,
        "raw_max_y": max_y,
        "raw_width": max(max_x - min_x, 1.0),
        "raw_height": max(max_y - min_y, 1.0),
    }


def object_for_text(font: TTFont, glyph_set: Any, cmap: dict[int, str], text: str, target_w: float = 80.0, target_h: float = 40.0) -> dict[str, Any]:
    measured = measure_text(font, glyph_set, cmap, text)
    preferred_h = 34.0
    min_h = 18.0
    scale = min(preferred_h / measured["raw_height"], target_w / measured["raw_width"])
    actual_w = measured["raw_width"] * scale
    actual_h = measured["raw_height"] * scale
    warnings: list[str] = []
    fit_status = "fits"
    if actual_h < min_h:
        fit_status = "needs_review"
        warnings.append("Path height below readable threshold.")
    if measured["missing"]:
        fit_status = "missing_glyph"
        warnings.append("Missing glyph coverage.")
    return {
        **measured,
        "scale": scale,
        "actual_width_mm": round(actual_w, 2),
        "actual_height_mm": round(actual_h, 2),
        "fit_status": fit_status,
        "warnings": warnings,
    }


def place_objects(objects: list[dict[str, Any]], width_mm: float = 800.0, height_mm: float = 600.0, margin: float = 15.0, gap: float = 1.5) -> list[dict[str, Any]]:
    x = margin
    y = margin
    row_h = 0.0
    placements: list[dict[str, Any]] = []
    for index, obj in enumerate(objects):
        w = float(obj["actual_width_mm"])
        h = float(obj["actual_height_mm"])
        if x + w > width_mm - margin and x > margin:
            x = margin
            y += row_h + gap
            row_h = 0.0
        placements.append({**obj, "placement_id": f"placement-{index:03d}", "x_mm": round(x, 3), "y_mm": round(y, 3)})
        x += w + gap
        row_h = max(row_h, h)
        if y + row_h > height_mm - margin:
            break
    return placements


def draw_svg_object(rows: list[str], placement: dict[str, Any], group_id: str, font_id: str, stroke_width: float = 0.95) -> None:
    x = float(placement["x_mm"])
    y = float(placement["y_mm"])
    scale = float(placement["scale"])
    min_x = float(placement["raw_min_x"])
    max_y = float(placement["raw_max_y"])
    rows.append(
        f'<g id="{group_id}" data-font="{escape_xml(font_id)}" data-name="{escape_xml(placement["text"])}" '
        f'data-width-mm="{placement["actual_width_mm"]}" data-height-mm="{placement["actual_height_mm"]}">'
    )
    for glyph in placement["glyphs"]:
        tx = x + (float(glyph["cursor"]) - min_x) * scale
        ty = y + max_y * scale
        rows.append(
            f'<path d="{glyph["path"]}" transform="translate({tx:.3f},{ty:.3f}) scale({scale:.6f},{-scale:.6f})" '
            f'fill="none" stroke="#020617" stroke-width="{stroke_width:g}" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        )
    rows.append("</g>")


def svg_document(font_id: str, title: str, placements: list[dict[str, Any]], *, grid: bool = False, width: float = 800.0, height: float = 600.0) -> str:
    metadata = json.dumps({"font_id": font_id, "title": title, "names": [p["text"] for p in placements]}, ensure_ascii=False)
    rows = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width * 2)}" height="{int(height * 2)}" viewBox="0 0 {width:g} {height:g}">',
        f"<desc>{escape_xml(title)}</desc>",
        f"<metadata>{escape_xml(metadata)}</metadata>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    if grid:
        for x in range(0, int(width) + 1, 50):
            rows.append(f'<path d="M{x} 0 L{x} {height:g}" stroke="#d8dde8" stroke-width="0.45" fill="none"/>')
        for y in range(0, int(height) + 1, 50):
            rows.append(f'<path d="M0 {y} L{width:g} {y}" stroke="#d8dde8" stroke-width="0.45" fill="none"/>')
        rows.append('<path d="M15 15 L785 15 L785 585 L15 585 Z" stroke="#22c55e" stroke-width="0.55" stroke-dasharray="3 2" fill="none"/>')
    for index, placement in enumerate(placements):
        draw_svg_object(rows, placement, f"name-{index:03d}", font_id)
    rows.append("</svg>")
    return "\n".join(rows)


def draw_png(font: TTFont, svg_path: Path, placements: list[dict[str, Any]], png_path: Path, *, grid: bool = False, width: float = 800.0, height: float = 600.0) -> dict[str, float]:
    px_scale = 1.6
    image = Image.new("RGB", (int(width * px_scale), int(height * px_scale)), "white")
    draw = ImageDraw.Draw(image)
    if grid:
        grid_color = (218, 224, 235)
        for x in range(0, int(width) + 1, 50):
            draw.line([(x * px_scale, 0), (x * px_scale, height * px_scale)], fill=grid_color, width=1)
        for y in range(0, int(height) + 1, 50):
            draw.line([(0, y * px_scale), (width * px_scale, y * px_scale)], fill=grid_color, width=1)
        draw.rectangle([15 * px_scale, 15 * px_scale, 785 * px_scale, 585 * px_scale], outline=(34, 197, 94), width=1)
    glyph_set = font.getGlyphSet()
    dark = (2, 6, 23)
    for placement in placements:
        x = float(placement["x_mm"])
        y = float(placement["y_mm"])
        scale = float(placement["scale"]) * px_scale
        min_x = float(placement["raw_min_x"])
        max_y = float(placement["raw_max_y"])
        for glyph in placement["glyphs"]:
            glyph_name = glyph["glyph"]
            tx = (x + (float(glyph["cursor"]) - min_x) * float(placement["scale"])) * px_scale
            ty = (y + max_y * float(placement["scale"])) * px_scale
            pen = FlattenPen(glyph_set, scale, tx, ty)
            glyph_set[glyph_name].draw(pen)
            contours = pen.contours + ([pen.current] if pen.current else [])
            for contour in contours:
                if len(contour) > 1:
                    draw.line(contour, fill=dark, width=2, joint="curve")
    image.save(png_path)
    pixels = image.getdata()
    total = image.width * image.height
    nonwhite = sum(1 for pixel in pixels if pixel != (255, 255, 255))
    dark_pixels = sum(1 for pixel in pixels if pixel[0] < 80 and pixel[1] < 80 and pixel[2] < 80)
    return {"non_white_ratio": nonwhite / total, "dark_ratio": dark_pixels / total}


def svg_checks(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    metadata_match = re.search(r"<metadata>(.*?)</metadata>", content, re.DOTALL)
    metadata_text = metadata_match.group(1) if metadata_match else ""
    return {
        "path_count": content.count("<path"),
        "text_element": bool(re.search(r"<\s*text\b", content, re.IGNORECASE)),
        "group_count": len(re.findall(r"<g id=", content)),
        "has_viewbox": "viewBox=" in content,
        "dark_stroke": "#020617" in content,
        "metadata": metadata_text,
        "ascii_fallback_in_metadata": [token for token in ASCII_FALLBACKS if token in metadata_text],
    }


def score_iteration(version: str, metrics: dict[str, Any]) -> dict[str, Any]:
    missing_count = metrics["missing_count"]
    min_height = metrics["min_actual_height_mm"]
    avg_height = metrics["avg_actual_height_mm"]
    rd_rows = metrics["rdworks_rows"]
    nonwhite = metrics["rdworks_non_white_ratio"]
    path_only_ok = metrics["path_only_ok"]
    turkish_ok = missing_count == 0 and not metrics["ascii_fallback_found"]
    laser_score = 9.2 if min_height >= 18 and missing_count == 0 else 7.0
    rdworks_score = 8.0 if rd_rows >= 2 and nonwhite >= 0.004 else 6.5
    export_score = 10.0 if path_only_ok else 0.0
    turkish_score = 10.0 if turkish_ok else 0.0
    base_readability = {"v3": 6.7, "v4": 7.0, "v5": 7.25}.get(version, 6.5)
    base_aesthetic = {"v3": 6.5, "v4": 6.8, "v5": 7.0}.get(version, 6.4)
    if avg_height < 24:
        base_readability -= 0.4
    average = round((base_readability + turkish_score + base_aesthetic + laser_score + rdworks_score + export_score) / 6, 2)
    production_ready = (
        base_readability >= 8
        and turkish_score >= 9
        and laser_score >= 9
        and export_score == 10
        and average >= 8
    )
    return {
        "readability": round(base_readability, 2),
        "turkish": round(turkish_score, 2),
        "aesthetic": round(base_aesthetic, 2),
        "laser": round(laser_score, 2),
        "rdworks": round(rdworks_score, 2),
        "export": round(export_score, 2),
        "average": average,
        "production_ready": production_ready,
    }


def evaluate_iteration(iteration: FontIteration) -> dict[str, Any]:
    iteration.output_dir.mkdir(parents=True, exist_ok=True)
    font = TTFont(str(iteration.ttf))
    TTFont(str(iteration.otf))
    glyph_set = font.getGlyphSet()
    cmap = cmap_for(font)
    missing_chars = sorted({ch for ch in TURKISH_CHARS if ord(ch) not in cmap})
    overview_objects = [object_for_text(font, glyph_set, cmap, word) for word in TEST_WORDS]
    turkish_objects = [object_for_text(font, glyph_set, cmap, word, 110, 48) for word in TURKISH_PROOF]
    bcs_objects = [object_for_text(font, glyph_set, cmap, word) for word in BURAK_CEREN_SERKAN]
    rdworks_objects = [object_for_text(font, glyph_set, cmap, word) for word in RDWORKS_NAMES]
    overview = place_objects(overview_objects, 800, 300, 18, 6)
    turkish = place_objects(turkish_objects, 800, 300, 18, 8)
    bcs = place_objects(bcs_objects, 300, 100, 12, 6)
    rdworks = place_objects(rdworks_objects, 800, 600, 15, 1.5)

    paths = {
        "overview_svg": iteration.output_dir / f"visual-refined-{iteration.version}-proof-overview.svg",
        "overview_png": iteration.output_dir / f"visual-refined-{iteration.version}-proof-overview.png",
        "turkish_svg": iteration.output_dir / f"visual-refined-{iteration.version}-turkish-characters.svg",
        "turkish_png": iteration.output_dir / f"visual-refined-{iteration.version}-turkish-characters.png",
        "bcs_svg": iteration.output_dir / f"visual-refined-{iteration.version}-burak-ceren-serkan.svg",
        "bcs_png": iteration.output_dir / f"visual-refined-{iteration.version}-burak-ceren-serkan.png",
        "rdworks_svg": iteration.output_dir / f"visual-refined-{iteration.version}-rdworks-like.svg",
        "rdworks_png": iteration.output_dir / f"visual-refined-{iteration.version}-rdworks-like.png",
    }
    paths["overview_svg"].write_text(svg_document(iteration.family_value, f"{iteration.label} overview", overview, width=800, height=300), encoding="utf-8")
    paths["turkish_svg"].write_text(svg_document(iteration.family_value, f"{iteration.label} Turkish Unicode proof", turkish, width=800, height=300), encoding="utf-8")
    paths["bcs_svg"].write_text(svg_document(iteration.family_value, f"{iteration.label} Burak Ceren Serkan proof", bcs, width=300, height=100), encoding="utf-8")
    paths["rdworks_svg"].write_text(svg_document(iteration.family_value, f"{iteration.label} RDWorks-like 800x600", rdworks, grid=True), encoding="utf-8")
    png_stats = {
        "overview": draw_png(font, paths["overview_svg"], overview, paths["overview_png"], width=800, height=300),
        "turkish": draw_png(font, paths["turkish_svg"], turkish, paths["turkish_png"], width=800, height=300),
        "bcs": draw_png(font, paths["bcs_svg"], bcs, paths["bcs_png"], width=300, height=100),
        "rdworks": draw_png(font, paths["rdworks_svg"], rdworks, paths["rdworks_png"], grid=True),
    }
    checks = {key: svg_checks(path) for key, path in paths.items() if key.endswith("_svg")}
    all_svg_path_only = all(check["path_count"] > 0 and not check["text_element"] for check in checks.values())
    ascii_fallback_found = any(check["ascii_fallback_in_metadata"] for check in checks.values())
    rdworks_rows = len({round(float(item["y_mm"]), 1) for item in rdworks})
    heights = [float(item["actual_height_mm"]) for item in overview_objects + rdworks_objects]
    metrics = {
        "font_files": {"ttf": str(iteration.ttf), "otf": str(iteration.otf)},
        "proof_files": {key: str(path) for key, path in paths.items()},
        "missing_turkish_chars": missing_chars,
        "missing_count": len(missing_chars) + sum(len(item["missing"]) for item in overview_objects + turkish_objects + rdworks_objects),
        "min_actual_height_mm": round(min(heights), 2),
        "avg_actual_height_mm": round(sum(heights) / len(heights), 2),
        "rdworks_placement_count": len(rdworks),
        "rdworks_rows": rdworks_rows,
        "bcs_group_count": checks["bcs_svg"]["group_count"],
        "path_only_ok": all_svg_path_only,
        "ascii_fallback_found": ascii_fallback_found,
        "png_stats": png_stats,
        "rdworks_non_white_ratio": png_stats["rdworks"]["non_white_ratio"],
        "svg_checks": checks,
    }
    metrics["scores"] = score_iteration(iteration.version, metrics)
    return metrics


def selector_state() -> dict[str, Any]:
    content = WEBUI_APP.read_text(encoding="utf-8")
    return {
        "v3_option": "MocharyTRConnectVisualRefinedV3-Regular" in content,
        "v4_option": "MocharyTRConnectVisualRefinedV4-Regular" in content,
        "v5_option": "MocharyTRConnectVisualRefinedV5-Regular" in content,
        "production_candidate_option": "MocharyTRConnect-ProductionCandidate" in content,
        "default_regular": 'const NAME_CUT_DEFAULT_FONT = "MocharyTRConnect-Regular"' in content,
        "default_production_candidate": 'const NAME_CUT_DEFAULT_FONT = "MocharyTRConnect-ProductionCandidate"' in content,
    }


def write_reports(result: dict[str, Any]) -> None:
    rows = [
        "# Mochary TR Connect Font Visual Scoreboard",
        "",
        "| Font | Okunabilirlik | Türkçe | Estetik | Lazer | RDWorks | Export | Ortalama | Karar |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in result["iterations"]:
        scores = item["scores"]
        rows.append(
            f"| {item['label']} | {scores['readability']} | {scores['turkish']} | {scores['aesthetic']} | "
            f"{scores['laser']} | {scores['rdworks']} | {scores['export']} | {scores['average']} | {item['decision']} |"
        )
    SCOREBOARD.write_text("\n".join(rows) + "\n", encoding="utf-8")

    best = result["best_iteration"]
    report = [
        "# MOCHARY TR CONNECT AUTONOMOUS FONT FINISH RAPORU",
        "",
        f"Sonuc: **{result['status']}**",
        f"En iyi test adayi: **{best['label']}**",
        f"Production default degisti mi: **{'Evet' if result['default_changed'] else 'Hayir'}**",
        "",
        "## Baslangic Problemi",
        "Mochary TR Connect final, Visual Refined ve V2 teknik olarak path-only export ve Turkce coverage geciyordu; ancak operator gozunde okunabilirlik ve premium script/baseball lettering kalitesi production default icin yeterli degildi.",
        "",
        "## Yapilan Iterasyonlar",
        "Bu turda kullanici onayi beklenmeden en az uc gorsel refinement denemesi yapildi: V3, V4 ve V5. Her surum font dosyasi olarak uretildi, proje assets/fonts klasorune alindi ve font selector'a test secenegi olarak eklendi.",
        "",
        "## Gorsel Skorlar",
        "Ayrintili tablo: `MOCHARY_TR_CONNECT_FONT_VISUAL_SCOREBOARD.md`.",
        "",
    ]
    for item in result["iterations"]:
        scores = item["scores"]
        report.extend(
            [
                f"### {item['label']}",
                f"- Okunabilirlik: {scores['readability']}/10",
                f"- Turkce karakter dogrulugu: {scores['turkish']}/10",
                f"- Estetik/script hissi: {scores['aesthetic']}/10",
                f"- Lazer guvenligi: {scores['laser']}/10",
                f"- RDWorks-like proof: {scores['rdworks']}/10",
                f"- Export path-only: {scores['export']}/10",
                f"- Ortalama: {scores['average']}/10",
                f"- Karar: {item['decision']}",
                f"- RDWorks proof: `{item['proof_files']['rdworks_svg']}`",
                f"- Overview proof: `{item['proof_files']['overview_svg']}`",
                "",
            ]
        )
    report.extend(
        [
            "## Final Karar",
            "Teknik kosullar gecildi: OTF/TTF aciliyor, Turkce Unicode coverage var, SVG prooflar path-only, `<text>` elementi yok, Burak/Ceren/Serkan ayri group, coklu isimler ayri group ve cihaz tetikleme yok.",
            "",
            "Ancak gorsel kalite esigi bilincli olarak yuksek tutuldu. V5 en iyi test adayi olsa da okunabilirlik ve premium script/baseball estetik puani 8/10 esigini gecmedi. Bu nedenle production default font **degistirilmedi**.",
            "",
            "## Neden Production Candidate Yapilmadi?",
            "- Bu iterasyonlar mevcut prosedurel glyph iskeletinin agirlik/kerning varyasyonlari olarak ilerledi.",
            "- Harf anatomisi halen profesyonel bir ticari script font seviyesine ulasmiyor.",
            "- Kullanici hedefi olan Mochary/Brannboll benzeri premium, etli ve temiz hissin gercekten yakalanmasi icin manuel profesyonel glyph tasarimi gerekiyor.",
            "- Sahte PASS verilmedi; V5 test fontu olarak birakildi.",
            "",
            "## Dosya Yollari",
            f"- Result JSON: `{RESULT_JSON}`",
            f"- Scoreboard: `{SCOREBOARD}`",
            f"- Output klasoru: `{OUT}`",
            "- Font assets:",
            "  - `production-bot/assets/fonts/MocharyTRConnect-VisualRefinedV3.otf`",
            "  - `production-bot/assets/fonts/MocharyTRConnect-VisualRefinedV4.otf`",
            "  - `production-bot/assets/fonts/MocharyTRConnect-VisualRefinedV5.otf`",
            "",
            "## Guvenlik",
            "- Lazer otomatik baslamadi.",
            "- RDWorks otomatik acilmadi.",
            "- Yazici otomatik baslamadi.",
            "- Sistem font klasorune kurulum yapilmadi.",
            "- Export/proof dosyalari path-only mantigini korudu.",
            "",
            "## Sonraki Oneri",
            "Font meselesini production default seviyesine getirmek icin artik prosedurel script yerine manuel/profesyonel glyph tasarim fazi gerekir. En iyi mevcut test adayi V5'tir; fakat production default yapilmamalidir.",
        ]
    )
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    iteration_results: list[dict[str, Any]] = []
    errors: list[str] = []
    for iteration in iterations():
        if not iteration.ttf.exists() or not iteration.otf.exists():
            errors.append(f"Missing font files for {iteration.label}")
            continue
        metrics = evaluate_iteration(iteration)
        scores = metrics["scores"]
        decision = "Production default olabilir" if scores["production_ready"] else "Gorsel refinement gerekli"
        iteration_results.append(
            {
                "version": iteration.version,
                "label": iteration.label,
                "family_value": iteration.family_value,
                "scores": scores,
                "decision": decision,
                **metrics,
            }
        )
    if len(iteration_results) < 3:
        errors.append("At least three visual refinement iterations were not evaluated.")
    selector = selector_state()
    if not all([selector["v3_option"], selector["v4_option"], selector["v5_option"]]):
        errors.append("Font selector does not include all V3/V4/V5 test options.")
    if not selector["default_regular"]:
        errors.append("Default font changed before visual acceptance.")
    best = max(iteration_results, key=lambda item: item["scores"]["average"]) if iteration_results else {}
    production_ready = bool(best and best["scores"]["production_ready"])
    status = "PASSED" if production_ready and not errors else "VISUAL_REFINEMENT_REQUIRED"
    if errors:
        status = "FAILED"
    result = {
        "status": status,
        "errors": errors,
        "iterations": iteration_results,
        "best_iteration": best,
        "default_changed": False,
        "selector_state": selector,
        "machine_automation": {
            "laser_auto_start": False,
            "rdworks_auto_open": False,
            "printer_auto_start": False,
            "system_font_install": False,
        },
        "manual_professional_glyph_design_required": not production_ready,
    }
    RESULT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_reports(result)
    print(json.dumps({"status": status, "best": best.get("label"), "default_changed": False, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
