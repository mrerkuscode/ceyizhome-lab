from __future__ import annotations

import binascii
from dataclasses import dataclass
import json
import math
import re
import statistics
import unicodedata
import zlib
from pathlib import Path
from typing import Any


REFERENCE_FILE_NAMES = [
    "4. mayıs gümüş isimler.ai",
    "30 mart gold 01.ai",
    "30 mart gold 02.ai",
    "31 mart gümüş.ai",
    "03 gold cyzella.ai",
    "gold 01 cyzella.ai",
    "4 mayıs gold 03.ai",
]

OPTIONAL_REFERENCE_FILE_NAMES = [
    "02 gold cyzella.ai",
]


@dataclass(frozen=True)
class CorelReferencePath:
    commands: list[tuple[str, tuple[float, ...]]]
    closed: bool


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return ascii_value or "corel-reference"


def reference_name_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def resolve_reference_files(downloads_dir: Path) -> tuple[list[Path], list[Path], list[str]]:
    available = { _nfc(path.name): path for path in downloads_dir.glob("*.ai") }
    required: list[Path] = []
    missing: list[str] = []
    for name in REFERENCE_FILE_NAMES:
        path = available.get(_nfc(name))
        if path:
            required.append(path)
        else:
            missing.append(name)
    optional = [available[_nfc(name)] for name in OPTIONAL_REFERENCE_FILE_NAMES if _nfc(name) in available]
    return required, optional, missing


def _extract_pdf_streams(data: bytes) -> list[bytes]:
    streams: list[bytes] = []
    for match in re.finditer(rb"(\d+)\s+0\s+obj(.*?)endobj", data, re.S):
        obj = match.group(2)
        start = obj.find(b"stream")
        end = obj.rfind(b"endstream")
        if start < 0 or end <= start:
            continue
        stream = obj[start + len(b"stream"):end]
        if stream.startswith(b"\r\n"):
            stream = stream[2:]
        elif stream.startswith(b"\n"):
            stream = stream[1:]
        if stream.endswith(b"\r\n"):
            stream = stream[:-2]
        elif stream.endswith(b"\n"):
            stream = stream[:-1]
        streams.append(stream)
    return streams


def _decode_private_stream(stream: bytes) -> bytes:
    raw = stream.strip()
    if raw.startswith(b"x\x9c") or raw.startswith(b"x\xda"):
        return zlib.decompress(raw)
    hex_candidate = b"".join(re.findall(rb"[0-9A-Fa-f]+", raw))
    if len(hex_candidate) > 100 and hex_candidate[:4].lower() in {b"789c", b"78da"}:
        if len(hex_candidate) % 2:
            hex_candidate = hex_candidate[:-1]
        return zlib.decompress(binascii.unhexlify(hex_candidate))
    return raw


def extract_ai_private_data(path: Path) -> str:
    candidates: list[bytes] = []
    for stream in _extract_pdf_streams(path.read_bytes()):
        try:
            decoded = _decode_private_stream(stream)
        except Exception:
            continue
        if b"%!PS-Adobe" in decoded and b"Exported from CorelDRAW" in decoded:
            candidates.append(decoded)
    if not candidates:
        raise ValueError(f"{path}: AIPrivateData/CorelDRAW private stream bulunamadı.")
    private = max(candidates, key=len)
    return private.decode("latin1", errors="replace")


def _numbers(line: str) -> list[float]:
    return [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", line)]


def parse_ai_private_paths(private_data: str) -> list[CorelReferencePath]:
    paths: list[CorelReferencePath] = []
    current: list[tuple[str, tuple[float, ...]]] = []
    in_artwork = False
    for raw_line in private_data.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("%%EndSetup") or line.startswith("%AI5_BeginLayer"):
            in_artwork = True
            continue
        if not in_artwork or line.startswith("%"):
            continue
        command = line.split()[-1] if line.split() else ""
        vals = _numbers(line)
        if command == "m" and len(vals) >= 2:
            if len(current) > 1:
                paths.append(CorelReferencePath(current, closed=False))
            current = [("M", (vals[-2], vals[-1]))]
        elif command in {"L", "l"} and current and len(vals) >= 2:
            current.append(("L", (vals[-2], vals[-1])))
        elif command in {"C", "c"} and current and len(vals) >= 6:
            current.append(("C", tuple(vals[-6:])))
        elif command in {"s", "f", "F", "b", "B"}:
            if len(current) > 1:
                paths.append(CorelReferencePath(current, closed=True))
            current = []
        elif command == "S":
            if len(current) > 1:
                paths.append(CorelReferencePath(current, closed=False))
            current = []
    if len(current) > 1:
        paths.append(CorelReferencePath(current, closed=False))
    return paths


def _points_from_paths(paths: list[CorelReferencePath]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for path in paths:
        for command, values in path.commands:
            if command in {"M", "L"}:
                points.append((values[0], values[1]))
            elif command == "C":
                points.extend([(values[0], values[1]), (values[2], values[3]), (values[4], values[5])])
    return points


def bbox_for_paths(paths: list[CorelReferencePath]) -> tuple[float, float, float, float] | None:
    points = _points_from_paths(paths)
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _path_length_proxy(path: CorelReferencePath) -> float:
    total = 0.0
    last: tuple[float, float] | None = None
    first: tuple[float, float] | None = None
    for command, values in path.commands:
        if command == "M":
            last = (values[0], values[1])
            first = last
        elif command == "L" and last:
            point = (values[0], values[1])
            total += math.dist(last, point)
            last = point
        elif command == "C" and last:
            controls = [(values[0], values[1]), (values[2], values[3]), (values[4], values[5])]
            previous = last
            for point in controls:
                total += math.dist(previous, point)
                previous = point
            last = controls[-1]
    if path.closed and first and last:
        total += math.dist(last, first)
    return total


def metrics_for_paths(paths: list[CorelReferencePath]) -> dict[str, Any]:
    bbox = bbox_for_paths(paths)
    curve_count = sum(1 for path in paths for command, _ in path.commands if command == "C")
    line_count = sum(1 for path in paths for command, _ in path.commands if command == "L")
    move_count = sum(1 for path in paths for command, _ in path.commands if command == "M")
    closed_count = sum(1 for path in paths if path.closed)
    width = height = area = aspect = 0.0
    if bbox:
        width = max(0.0, bbox[2] - bbox[0])
        height = max(0.0, bbox[3] - bbox[1])
        area = max(1.0, width * height)
        aspect = round(width / height, 4) if height else 0.0
    length_proxy = sum(_path_length_proxy(path) for path in paths)
    return {
        "pathCount": len(paths),
        "closedPathCount": closed_count,
        "moveCount": move_count,
        "lineCount": line_count,
        "curveCount": curve_count,
        "bbox": [round(value, 3) for value in bbox] if bbox else [],
        "bboxWidth": round(width, 3),
        "bboxHeight": round(height, 3),
        "bboxAspect": aspect,
        "lengthProxy": round(length_proxy, 3),
        "curveDensity": round(curve_count / area, 7),
        "pathDensity": round(len(paths) / area, 7),
        "avgCurvesPerPath": round(curve_count / max(1, len(paths)), 3),
        "closedRatio": round(closed_count / max(1, len(paths)), 4),
    }


def _boxes_touch(a: tuple[float, float, float, float], b: tuple[float, float, float, float], gap_x: float, gap_y: float) -> bool:
    return not (
        a[2] + gap_x < b[0]
        or b[2] + gap_x < a[0]
        or a[3] + gap_y < b[1]
        or b[3] + gap_y < a[1]
    )


def cluster_reference_paths(paths: list[CorelReferencePath]) -> list[list[CorelReferencePath]]:
    indexed: list[tuple[int, CorelReferencePath, tuple[float, float, float, float]]] = []
    heights: list[float] = []
    widths: list[float] = []
    for index, path in enumerate(paths):
        bbox = bbox_for_paths([path])
        if not bbox:
            continue
        width = max(0.0, bbox[2] - bbox[0])
        height = max(0.0, bbox[3] - bbox[1])
        if width <= 0 or height <= 0:
            continue
        indexed.append((index, path, bbox))
        heights.append(height)
        widths.append(width)
    if not indexed:
        return []
    median_h = statistics.median(heights)
    median_w = statistics.median(widths)
    gap_x = max(8.0, min(42.0, median_w * 1.35))
    gap_y = max(5.0, min(26.0, median_h * 0.65))
    parent = list(range(len(indexed)))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(a: int, b: int) -> None:
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for left in range(len(indexed)):
        for right in range(left + 1, len(indexed)):
            if _boxes_touch(indexed[left][2], indexed[right][2], gap_x, gap_y):
                union(left, right)
    groups: dict[int, list[CorelReferencePath]] = {}
    for local_index, (_, path, _) in enumerate(indexed):
        groups.setdefault(find(local_index), []).append(path)
    clusters = [group for group in groups.values() if len(group) >= 2]
    return sorted(clusters, key=lambda group: (bbox_for_paths(group) or (0, 0, 0, 0))[1])


def object_metrics_for_paths(paths: list[CorelReferencePath]) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for index, cluster in enumerate(cluster_reference_paths(paths), start=1):
        metrics = metrics_for_paths(cluster)
        # Ignore huge full-sheet clusters and tiny dust clusters. These bounds
        # keep the corpus focused on name-like objects while still accepting
        # decorative Corel outlines that are part of the production style.
        if metrics.get("pathCount", 0) < 2:
            continue
        if metrics.get("bboxWidth", 0) < 20 or metrics.get("bboxHeight", 0) < 8:
            continue
        objects.append({"objectIndex": index, **metrics})
    return objects


def reference_objects_for_paths(paths: list[CorelReferencePath]) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for index, cluster in enumerate(cluster_reference_paths(paths), start=1):
        metrics = metrics_for_paths(cluster)
        if metrics.get("pathCount", 0) < 2:
            continue
        if metrics.get("bboxWidth", 0) < 20 or metrics.get("bboxHeight", 0) < 8:
            continue
        objects.append({"objectIndex": index, "paths": cluster, "metrics": metrics})
    return objects


def aggregate_metrics(items: list[dict[str, Any]], keys: list[str]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for key in keys:
        values = [float(item.get(key) or 0.0) for item in items if item.get(key) is not None]
        if values:
            aggregate[key] = {
                "min": round(min(values), 6),
                "max": round(max(values), 6),
                "median": round(statistics.median(values), 6),
                "mean": round(statistics.fmean(values), 6),
            }
    return aggregate


def _transform_paths(paths: list[CorelReferencePath], view_w: float = 800.0, view_h: float = 600.0, margin: float = 20.0) -> list[str]:
    bbox = bbox_for_paths(paths)
    if not bbox:
        return []
    min_x, min_y, max_x, max_y = bbox
    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    scale = min((view_w - margin * 2) / width, (view_h - margin * 2) / height)
    ox = (view_w - width * scale) / 2
    oy = (view_h - height * scale) / 2

    def point(x: float, y: float) -> tuple[float, float]:
        return ox + (x - min_x) * scale, view_h - (oy + (y - min_y) * scale)

    svg_paths: list[str] = []
    for path in paths:
        commands: list[str] = []
        for command, values in path.commands:
            if command == "M":
                x, y = point(values[0], values[1])
                commands.append(f"M {x:.3f} {y:.3f}")
            elif command == "L":
                x, y = point(values[0], values[1])
                commands.append(f"L {x:.3f} {y:.3f}")
            elif command == "C":
                x1, y1 = point(values[0], values[1])
                x2, y2 = point(values[2], values[3])
                x3, y3 = point(values[4], values[5])
                commands.append(f"C {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} {x3:.3f} {y3:.3f}")
        if path.closed:
            commands.append("Z")
        if len(commands) > 1:
            svg_paths.append(" ".join(commands))
    return svg_paths


def write_reference_svg(path: Path, reference_paths: list[CorelReferencePath], title: str) -> dict[str, Any]:
    svg_paths = _transform_paths(reference_paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="800mm" height="600mm" viewBox="0 0 800 600" data-corel-reference="true">',
        f"<title>{title}</title>",
        '<rect x="0" y="0" width="800" height="600" fill="#ffffff"/>',
        '<g id="corel-reference-paths" fill="none" stroke="#020617" stroke-width="0.22" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke">',
    ]
    for index, data in enumerate(svg_paths, start=1):
        lines.append(f'<path id="corel-ref-path-{index}" d="{data}"/>')
    lines.extend(["</g>", "</svg>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"svgPath": str(path), "svgPathCount": len(svg_paths), "pathOnly": "<text" not in path.read_text(encoding="utf-8").lower()}


def analyze_reference_file(path: Path, required: bool = True, output_svg: Path | None = None) -> dict[str, Any]:
    private_data = extract_ai_private_data(path)
    reference_paths = parse_ai_private_paths(private_data)
    metrics = metrics_for_paths(reference_paths)
    object_metrics = object_metrics_for_paths(reference_paths)
    metadata = {
        "file": path.name,
        "path": str(path),
        "required": required,
        "sizeBytes": path.stat().st_size,
        "privateDataBytes": len(private_data.encode("latin1", errors="replace")),
        "corelDrawExported": "Exported from CorelDRAW" in private_data,
        "pdfCompatibleAi": path.read_bytes()[:8].startswith(b"%PDF-"),
        "aiBoundingBox": "",
        "title": "",
    }
    bbox_match = re.search(r"%%BoundingBox:([^\r\n]+)", private_data)
    title_match = re.search(r"%%Title:([^\r\n]+)", private_data)
    if bbox_match:
        metadata["aiBoundingBox"] = bbox_match.group(1).strip()
    if title_match:
        metadata["title"] = title_match.group(1).strip()
    svg_info: dict[str, Any] = {}
    if output_svg:
        svg_info = write_reference_svg(output_svg, reference_paths, f"Corel reference: {path.name}")
    return {**metadata, **metrics, "objectCount": len(object_metrics), "objectMetrics": object_metrics, **svg_info}


def build_reference_corpus(downloads_dir: Path, output_dir: Path | None = None) -> dict[str, Any]:
    required_paths, optional_paths, missing = resolve_reference_files(downloads_dir)
    references: list[dict[str, Any]] = []
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    for index, path in enumerate(required_paths + optional_paths, start=1):
        svg_path = None
        if output_dir:
            prefix = "required" if path in required_paths else "optional"
            svg_path = output_dir / f"{index:02d}-{prefix}-{_slug(path.stem)}.svg"
        references.append(analyze_reference_file(path, required=path in required_paths, output_svg=svg_path))
    numeric_keys = ["pathCount", "curveCount", "lineCount", "bboxAspect", "avgCurvesPerPath", "closedRatio", "curveDensity", "pathDensity"]
    aggregate = aggregate_metrics(references, numeric_keys)
    object_items = [item for reference in references for item in reference.get("objectMetrics", [])]
    object_aggregate = aggregate_metrics(object_items, numeric_keys + ["bboxWidth", "bboxHeight"])
    return {
        "status": "READY" if references and not missing else "MISSING_REQUIRED_REFERENCES",
        "downloadsDir": str(downloads_dir),
        "requiredCount": len(required_paths),
        "optionalCount": len(optional_paths),
        "missingRequired": missing,
        "references": references,
        "aggregate": aggregate,
        "objectCount": len(object_items),
        "objectAggregate": object_aggregate,
        "notes": [
            "AI/PDF normal page content may look empty; Corel reference vectors are read from Illustrator private data streams.",
            "Reference files do not expose name text; first version scores general Corel production style, not exact word identity.",
        ],
    }


def build_reference_object_library(downloads_dir: Path, output_dir: Path | None = None) -> dict[str, Any]:
    required_paths, optional_paths, missing = resolve_reference_files(downloads_dir)
    objects: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    object_dir = output_dir / "objects" if output_dir else None
    if object_dir:
        object_dir.mkdir(parents=True, exist_ok=True)
    for ref_index, path in enumerate(required_paths + optional_paths, start=1):
        required = path in required_paths
        private_data = extract_ai_private_data(path)
        reference_paths = parse_ai_private_paths(private_data)
        ref_objects = reference_objects_for_paths(reference_paths)
        references.append({
            "file": path.name,
            "path": str(path),
            "required": required,
            "objectCount": len(ref_objects),
            **metrics_for_paths(reference_paths),
        })
        for obj in ref_objects:
            object_index = int(obj["objectIndex"])
            object_id = f"{ref_index:02d}-{object_index:03d}-{_slug(path.stem)}"
            svg_info: dict[str, Any] = {}
            if object_dir:
                svg_info = write_reference_svg(
                    object_dir / f"{object_id}.svg",
                    obj["paths"],
                    f"Corel reference object: {path.name} / {object_index}",
                )
            objects.append({
                "objectId": object_id,
                "sourceFile": path.name,
                "sourcePath": str(path),
                "required": required,
                "sourceReferenceIndex": ref_index,
                "objectIndex": object_index,
                **obj["metrics"],
                **svg_info,
            })
    numeric_keys = ["pathCount", "curveCount", "lineCount", "bboxAspect", "avgCurvesPerPath", "closedRatio", "curveDensity", "pathDensity", "bboxWidth", "bboxHeight"]
    return {
        "status": "READY" if objects and not missing else "MISSING_REQUIRED_REFERENCES",
        "downloadsDir": str(downloads_dir),
        "requiredCount": len(required_paths),
        "optionalCount": len(optional_paths),
        "missingRequired": missing,
        "referenceCount": len(references),
        "references": references,
        "objectCount": len(objects),
        "objects": objects,
        "objectAggregate": aggregate_metrics(objects, numeric_keys),
        "notes": [
            "Object library splits Corel private-data paths into name-like visual groups.",
            "Source files do not expose text identity; object matching is visual/style matching, not word matching.",
        ],
    }


def score_against_object_library(candidate_metrics: dict[str, Any], library: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    scored: list[dict[str, Any]] = []
    for obj in library.get("objects", []) or []:
        score = 100.0
        reasons: list[str] = []
        for key, weight in [("bboxAspect", 36), ("closedRatio", 18), ("avgCurvesPerPath", 18), ("curveDensity", 10), ("pathDensity", 8)]:
            ref_value = float(obj.get(key) or 0.0)
            value = float(candidate_metrics.get(key) or 0.0)
            if ref_value <= 0 and value <= 0:
                continue
            tolerance = max(abs(ref_value) * (0.45 if key != "bboxAspect" else 0.32), 0.000001)
            penalty = min(weight, (abs(value - ref_value) / tolerance) * weight)
            if penalty > weight * 0.62:
                reasons.append(f"{key} uzak: aday={value:.5f}, ref={ref_value:.5f}")
            score -= penalty
        scored.append({
            "objectId": obj.get("objectId"),
            "sourceFile": obj.get("sourceFile"),
            "svgPath": obj.get("svgPath"),
            "score": round(max(0.0, min(100.0, score)), 2),
            "reasons": reasons,
            "referenceMetrics": {key: obj.get(key) for key in ["bboxAspect", "closedRatio", "avgCurvesPerPath", "curveDensity", "pathDensity", "pathCount", "curveCount"]},
        })
    scored.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    best = scored[0] if scored else {}
    best_score = float(best.get("score") or 0.0)
    status = "PASSED" if best_score >= 76 else "OBJECT_STYLE_REVIEW_REQUIRED" if best_score >= 58 else "OBJECT_REFERENCE_MISMATCH"
    return {
        "score": round(best_score, 2),
        "status": status,
        "bestObject": best,
        "matches": scored[:limit],
    }


def paths_to_svg_path_data(paths: list[CorelReferencePath]) -> str:
    parts: list[str] = []
    for path in paths:
        commands: list[str] = []
        for command, values in path.commands:
            if command == "M":
                commands.append(f"M {values[0]:.3f} {values[1]:.3f}")
            elif command == "L":
                commands.append(f"L {values[0]:.3f} {values[1]:.3f}")
            elif command == "C":
                commands.append(
                    f"C {values[0]:.3f} {values[1]:.3f} {values[2]:.3f} {values[3]:.3f} {values[4]:.3f} {values[5]:.3f}"
                )
        if path.closed:
            commands.append("Z")
        if len(commands) > 1:
            parts.append(" ".join(commands))
    return " ".join(parts)


def extract_svg_path_data(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return " ".join(re.findall(r"<path\b[^>]*\bd=[\"']([^\"']+)[\"']", text, re.I | re.S))


def extract_dxf_path_data(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    paths: list[str] = []
    current: list[tuple[float, float]] = []
    in_polyline = False
    index = 0
    while index < len(lines):
        code = lines[index].strip()
        value = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if code == "0" and value.upper() in {"POLYLINE", "LWPOLYLINE"}:
            if len(current) > 1:
                paths.append(" ".join([f"M {current[0][0]:.3f} {current[0][1]:.3f}"] + [f"L {x:.3f} {y:.3f}" for x, y in current[1:]] + ["Z"]))
            current = []
            in_polyline = True
            index += 2
            continue
        if code == "0" and value.upper() == "SEQEND":
            if len(current) > 1:
                paths.append(" ".join([f"M {current[0][0]:.3f} {current[0][1]:.3f}"] + [f"L {x:.3f} {y:.3f}" for x, y in current[1:]] + ["Z"]))
            current = []
            in_polyline = False
            index += 2
            continue
        if in_polyline and code == "10":
            try:
                x = float(value)
                y = 0.0
                if index + 3 < len(lines) and lines[index + 2].strip() == "20":
                    y = float(lines[index + 3].strip())
                    index += 4
                else:
                    index += 2
                current.append((x, y))
                continue
            except ValueError:
                pass
        index += 2
    if len(current) > 1:
        paths.append(" ".join([f"M {current[0][0]:.3f} {current[0][1]:.3f}"] + [f"L {x:.3f} {y:.3f}" for x, y in current[1:]] + ["Z"]))
    return " ".join(paths)


def load_exact_reference_path_data(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".svg":
        path_data = extract_svg_path_data(path)
    elif suffix == ".dxf":
        path_data = extract_dxf_path_data(path)
    elif suffix == ".ai":
        path_data = paths_to_svg_path_data(parse_ai_private_paths(extract_ai_private_data(path)))
    else:
        path_data = ""
    return {
        "path": str(path),
        "format": suffix.lstrip("."),
        "pathData": path_data,
        "pathOnly": bool(path_data),
        "metrics": path_geometry_metrics_from_svg_path(path_data) if path_data else {},
    }


def score_against_exact_reference(candidate_metrics: dict[str, Any], reference_metrics: dict[str, Any]) -> dict[str, Any]:
    score = 100.0
    reasons: list[str] = []
    for key, weight, tolerance_factor in [
        ("bboxAspect", 42, 0.18),
        ("closedRatio", 18, 0.24),
        ("avgCurvesPerPath", 16, 0.35),
        ("pathCount", 10, 0.35),
        ("curveCount", 8, 0.42),
        ("lineCount", 6, 0.55),
    ]:
        ref_value = float(reference_metrics.get(key) or 0.0)
        value = float(candidate_metrics.get(key) or 0.0)
        if ref_value <= 0 and value <= 0:
            continue
        tolerance = max(abs(ref_value) * tolerance_factor, 0.000001)
        penalty = min(weight, (abs(value - ref_value) / tolerance) * weight)
        if penalty > weight * 0.45:
            reasons.append(f"{key} exact referanstan uzak: aday={value:.5f}, ref={ref_value:.5f}")
        score -= penalty
    final_score = round(max(0.0, min(100.0, score)), 2)
    status = "EXACT_GOLDEN_PASSED" if final_score >= 86 else "EXACT_GOLDEN_REVIEW_REQUIRED" if final_score >= 72 else "EXACT_GOLDEN_MISMATCH"
    return {"score": final_score, "status": status, "reasons": reasons}


def path_geometry_metrics_from_svg_path(path_data: str) -> dict[str, Any]:
    tokens = re.findall(r"[MLCZ]|-?\d+(?:\.\d+)?", path_data or "")
    paths: list[CorelReferencePath] = []
    current: list[tuple[str, tuple[float, ...]]] = []
    index = 0
    command = ""
    while index < len(tokens):
        token = tokens[index]
        if token in {"M", "L", "C", "Z"}:
            command = token
            index += 1
            if command == "Z":
                if len(current) > 1:
                    paths.append(CorelReferencePath(current, closed=True))
                current = []
            continue
        if command == "M" and index + 1 < len(tokens):
            if len(current) > 1:
                paths.append(CorelReferencePath(current, closed=False))
            current = [("M", (float(tokens[index]), float(tokens[index + 1])))]
            command = "L"
            index += 2
        elif command == "L" and index + 1 < len(tokens):
            current.append(("L", (float(tokens[index]), float(tokens[index + 1]))))
            index += 2
        elif command == "C" and index + 5 < len(tokens):
            current.append(("C", tuple(float(tokens[index + offset]) for offset in range(6))))
            index += 6
        else:
            index += 1
    if len(current) > 1:
        paths.append(CorelReferencePath(current, closed=False))
    return metrics_for_paths(paths)


def score_against_corpus(candidate_metrics: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    aggregate = corpus.get("objectAggregate") or corpus.get("aggregate") or {}
    score = 100.0
    reasons: list[str] = []
    # We compare style envelopes, not exact word identity. Penalize only clear
    # mismatches so this can act as a guardrail without pretending to be a full
    # designer-eye replacement.
    for key, weight in [("bboxAspect", 12), ("closedRatio", 12), ("avgCurvesPerPath", 8), ("curveDensity", 10), ("pathDensity", 8)]:
        envelope = aggregate.get(key) or {}
        if not envelope:
            continue
        value = float(candidate_metrics.get(key) or 0.0)
        median = float(envelope.get("median") or 0.0)
        lo = float(envelope.get("min") or median)
        hi = float(envelope.get("max") or median)
        tolerance = max(abs(hi - lo), abs(median) * 0.45, 0.000001)
        distance = abs(value - median)
        penalty = min(weight, (distance / tolerance) * weight)
        if penalty > weight * 0.55:
            reasons.append(f"{key} reference envelope uzak: aday={value:.5f}, median={median:.5f}")
        score -= penalty
    status = "PASSED" if score >= 78 else "COREL_STYLE_REVIEW_REQUIRED" if score >= 62 else "REFERENCE_MISMATCH"
    return {
        "score": round(max(0.0, min(100.0, score)), 2),
        "status": status,
        "reasons": reasons,
    }


def dump_corpus(path: Path, corpus: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
