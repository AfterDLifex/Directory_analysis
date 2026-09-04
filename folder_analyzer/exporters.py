"""
Report exporters.

Each function takes an :class:`AnalysisResult` and writes a self-contained
report to disk.  The HTML report embeds SVG charts (no CDN / internet needed
so the report works offline on every OS), the Markdown report is a
human-readable summary, and JSON/CSV export the raw numbers for tooling.

All functions are pure I/O (no global state) and return the output path.
"""

from __future__ import annotations

import csv
import dataclasses
import html as _html
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .formats import format_number, format_size
from .models import AnalysisResult


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def serialize_result(result: AnalysisResult) -> Dict[str, Any]:
    """Return a JSON-serialisable dictionary view of an AnalysisResult."""
    data = dataclasses.asdict(result)
    # ``config`` is included for reproducibility; normalise path separators.
    data["root_path"] = os.path.abspath(data["root_path"])
    return data


def export_json(result: AnalysisResult, output_path: str) -> str:
    """Write the full analysis as pretty-printed JSON."""
    data = serialize_result(result)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=True, default=str)
    return output_path


def export_csv(result: AnalysisResult, output_path: str) -> str:
    """Write the file-type breakdown as a CSV report."""
    cols = ["type", "label", "category", "files", "size",
            "size_formatted", "percentage"]
    with open(output_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in result.file_types:
            writer.writerow({c: row.get(c, "") for c in cols})
        # summary row
        writer.writerow({
            "type": "TOTAL", "label": "", "category": "",
            "files": format_number(result.total_files),
            "size": result.total_storage,
            "size_formatted": result.total_storage_formatted,
            "percentage": 100.0,
        })
    return output_path


def export_txt(result: AnalysisResult, output_path: str) -> str:
    """Write a compact, readable plain-text summary."""
    r = result
    lines: List[str] = []
    lines.append("Folder Storage Analytics - Summary Report")
    lines.append("=" * 50)
    lines.append(f"Folder : {r.root_path}")
    lines.append(f"Scan at: {r.generated_at}")
    lines.append(f"Duration: {r.scan_duration_seconds}s")
    lines.append("")
    lines.append(f"Total files       : {format_number(r.total_files)}")
    lines.append(f"Total directories : {format_number(r.total_directories)}")
    lines.append(f"Total storage     : {r.total_storage_formatted}")
    lines.append(f"Average file size : {r.avg_file_size_formatted}")
    lines.append("")

    def block(title, rows, fmt):
        lines.append(title)
        lines.append("-" * len(title))
        for row in rows:
            lines.append(fmt(row))
        lines.append("")

    block("File types (top {})".format(r.config.top_n),
          r.file_types,
          lambda d: f"  {d['label']:<18} {d['files']:>8} files  {d['size_formatted']:>12}  {d['percentage']}%")
    block("Categories", r.categories,
          lambda d: f"  {d['name']:<16} {d['files']:>8} files  {d['size_formatted']:>12}  {d['percentage']}%")
    block("Age distribution", r.age_distribution,
          lambda d: f"  {d['category']:<22} {d['files']:>8} files  {d['size_formatted']:>12}  {d['percentage']}%")
    block("Size distribution", r.size_distribution,
          lambda d: f"  {d['range']:<18} {d['count']:>8} files  {d['percentage']}%")
    block("Directory depth", r.depth_distribution,
          lambda d: f"  Level {d['depth']}  {d['files']:>8} dirs  {d['percentage']}%")

    if r.duplicate_groups:
        lines.append("Duplicate files")
        lines.append("-" * 15)
        lines.append(f"  Wasted space: {r.duplicate_wasted_formatted} "
                     f"across {len(r.duplicate_groups)} group(s)")
        for g in r.duplicate_groups[:10]:
            lines.append(f"  - {g['count']} copies of {g['size_formatted']} "
                         f"(wasted {g['wasted_formatted']}): "
                         + ", ".join(Path(f["path"]).name for f in g["files"]))
        lines.append("")

    lines.append("Key insights")
    lines.append("-" * 12)
    for ins in r.key_insights:
        lines.append("  " + ins)
    lines.append("")
    if r.warnings:
        lines.append("Warnings")
        lines.append("-" * 8)
        for w in r.warnings:
            lines.append("  " + w)
        lines.append("")
    if r.tree_text:
        lines.append("Tree")
        lines.append("-" * 4)
        lines.append(r.tree_text)
        lines.append("")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return output_path


# ---------------------------------------------------------------------------
# Inline SVG charts (self-contained, no CDN)
# ---------------------------------------------------------------------------

def _esc(text: Any) -> str:
    """HTML-escape arbitrary text for safe embedding."""
    return _html.escape(str(text))


def _svg_donut(data: List[Dict[str, Any]], size: int = 220, label: str = "") -> str:
    """Build a self-contained SVG donut chart."""
    if not data:
        return f'<svg width="{size}" height="{size}"></svg>'
    total = sum(max(d.get("size", 0), d.get("count", 0)) for d in data) or 1
    cx, cy, r = size / 2, size / 2, size / 2 - 24
    inner = r * 0.55
    strokes = []
    names = []
    start_a = 0.0
    for i, d in enumerate(data):
        val = max(d.get("size", 0), d.get("count", 0))
        pct = val / total
        end_a = start_a + pct * 360
        large = 1 if pct > 0.5 else 0
        sweep = 1 if (end_a - start_a) <= 180 else 0
        x1 = cx + r * _cosd(start_a)
        y1 = cy + r * _snd(start_a)
        x2 = cx + r * _cosd(end_a)
        y2 = cy + r * _snd(end_a)
        color = d.get("color", "#888888")
        strokes.append(
            f'<path d="M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large} {sweep} {x2:.2f} {y2:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{inner}" />'
        )
        lbl = d.get("label") or d.get("category") or d.get("range") or d.get("name", "?")
        names.append(f'<span style="color:{color}">■</span> {_esc(lbl)} ({pct*100:.1f}%)')
        start_a = end_a
    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="ui-serif">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#1e2230"/>'
        + "".join(strokes) +
        f'<text x="{cx}" y="{cy}" text-anchor="middle" dy="0.35em" '
        f'fill="#e4e6eb" font-size="14" font-weight="bold">{_esc(label)}</text>'
        f'</svg>'
    )
    legend = '<div style="margin-top:8px">' + " ".join(names) + "</div>"
    return f'<div style="text-align:center">{svg}{legend}</div>'


def _svg_bar(data: List[Dict[str, Any]], width: int = 480, height: int = 270) -> str:
    """Build a self-contained horizontal SVG bar chart."""
    if not data:
        return f'<svg width="{width}" height="{height}"></svg>'
    max_val = max((d.get("size", 0) or d.get("count", 0)) for d in data) or 1
    bar_h = 22
    gap = 8
    y = 40
    parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" font-family="ui-serif">',
        f'<rect width="{width}" height="{height}" fill="#1e2230"/>',
    ]
    for d in data:
        val = d.get("size", 0) or d.get("count", 0)
        w = (val / max_val) * (width - 160)
        lbl = d.get("name") or d.get("label") or d.get("category") or d.get("range", "?")
        parts.append(
            f'<rect x="5" y="{y}" width="{w:.1f}" height="{bar_h}" rx="4" '
            f'fill="{d.get("color", "#888888")}"/>'
        )
        parts.append(
            f'<text x="5" y="{y + bar_h/2 + 4}" font-size="12" fill="#9aa0a6">{_esc(lbl)}</text>'
        )
        parts.append(
            f'<text x="{width-5}" y="{y + bar_h/2 + 4}" text-anchor="end" font-size="12" fill="#9aa0a6">'
            f'{format_number(val)}</text>'
        )
        parts.append(
            f'<text x="{width-5}" y="{y + bar_h/2 + 4}" text-anchor="end" font-size="12" fill="#9aa0a6" dx="-4">'
            f'  {format_size(val)}</text>'
        )
        y += bar_h + gap
    parts.append(f'<line x1="5" y1="{y}" x2="{width-5}" y2="{y}" stroke="#3a3f4b" stroke-width="1"/>')
    parts.append("</svg>")
    return "".join(parts)


def _cosd(a: float) -> float:
    import math
    return math.cos(math.radians(a))


def _snd(a: float) -> float:
    import math
    return math.sin(math.radians(a))
def _html_table(rows: List[Dict[str, Any]], cols: List[str], headers=None) -> str:
    """Render a list of dicts as a styled HTML table."""
    head = headers or cols
    cells = "".join(f"<th>{_esc(h)}</th>" for h in head)
    body = []
    for row in rows:
        body.append("".join(f"<td>{_esc(row.get(c, ''))}</td>" for c in cols))
    return (
        '<table class="t"><thead><tr>' + cells + "</tr></thead><tbody>"
        + "".join(f"<tr>{b}</tr>" for b in body) + "</tbody></table>"
    )


def _summary_cards(r: AnalysisResult) -> str:
    cells = [
        ("Files", format_number(r.total_files)),
        ("Folders", format_number(r.total_directories)),
        ("Storage", r.total_storage_formatted),
        ("Avg size", r.avg_file_size_formatted),
    ]
    return "".join(
        f'<div class=card><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in cells
    )


def export_html(result: AnalysisResult, output_path: str, title: str = "Folder Analysis") -> str:
    """Write a self-contained, offline HTML report with embedded SVG charts."""
    r = result
    css = """
    body{margin:0;background:#0f131a;color:#e4e6eb;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
    .wrap{max-width:1100px;margin:0 auto;padding:28px}
    h1{font-size:26px;margin:0 0 4px}
    .sub{color:#9aa0a6;font-size:14px;margin-bottom:22px}
    .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
    .card{background:#161b22;border:1px solid #272d36;border-radius:12px;padding:16px;text-align:center}
    .card .k{font-size:13px;color:#9aa0a6;text-transform:uppercase;letter-spacing:.04em}
    .card .v{font-size:24px;font-weight:700;margin-top:4px}
    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px}
    .panel{background:#161b22;border:1px solid #272d36;border-radius:14px;padding:18px;margin-bottom:22px}
    .panel h2{font-size:17px;margin:0 0 14px}
    .t{width:100%;border-collapse:collapse;font-size:13px}
    .t th,.t td{padding:7px 10px;text-align:left;border-bottom:1px solid #272d36}
    .t th{color:#9aa0a6;text-transform:uppercase;font-size:11px;letter-spacing:.04em}
    .t td:first-child{color:#c9d1d9}
    .chart{text-align:center;margin:10px 0}
    .tree{background:#0d1116;border:1px solid #272d36;border-radius:10px;padding:14px;font-family:'SFMono-Regular',Consolas,monospace;font-size:12px;white-space:pre-wrap;color:#c9d1d9;overflow:auto}
    .ins li{margin:6px 0}
    .warn{color:#f5c518}
    """
    parts = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        f"<title>{_esc(title)}</title><style>{css}</style></head><body>",
        "<div class=wrap>",
        f"<h1>{_esc(title)}</h1>",
        f"<div class=sub>{_esc(r.root_path)} · generated {_esc(r.generated_at)} "
        f"· {r.scan_duration_seconds}s · {format_number(r.total_files)} files · "
        f"{r.total_storage_formatted}</div>",
        f'<div class=cards>{_summary_cards(r)}</div>',
        '<div class="grid2">',
        f'<div class=panel><h2>Storage by file type</h2><div class=chart>{_svg_donut(r.file_types[:8], label="file types")}</div></div>',
        f'<div class=panel><h2>Storage by category</h2><div class=chart>{_svg_donut(r.categories, label="categories")}</div></div>',
        "</div>",
        '<div class="panel"><h2>Top directories</h2>' + _svg_bar(r.top_directories[:10]) + "</div>",
        '<div class="grid2">',
        f'<div class=panel><h2>Age distribution</h2>{_svg_bar(r.age_distribution)}</div>',
        f'<div class=panel><h2>Size distribution</h2>{_svg_bar(r.size_distribution)}</div>',
        "</div>",
        '<div class="panel"><h2>By extension</h2>' + _html_table(
            r.file_types[:15], ["label", "category", "files", "size_formatted", "percentage"]) + "</div>",
        '<div class="panel"><h2>Largest files</h2>' + _html_table(
            r.largest_files[:15], ["name", "parent", "type", "size_formatted", "modified_formatted"]) + "</div>",
    ]
    if r.duplicate_groups:
        parts.append('<div class="panel"><h2>Duplicate files '
                     f'(wasted {_esc(r.duplicate_wasted_formatted)})</h2>')
        for g in r.duplicate_groups[:10]:
            names = ", ".join(Path(f["path"]).name for f in g["files"])
            parts.append(
                f'<div style="margin:6px 0"><b>{format_number(g["count"])} copies</b> '
                f'· {_esc(g["size_formatted"])} each · <span class=warn>wasted {_esc(g["wasted_formatted"])}</span><br>'
                f'<span style="color:#9aa0a6">{_esc(names)}</span></div>'
            )
        parts.append("</div>")
    parts.append('<div class="panel"><h2>Directory tree</h2><pre class=tree>'
                 + _esc(r.tree_text) + "</pre></div>")
    parts.append('<div class="panel"><h2>Key insights</h2><ul class=ins>'
                 + "".join(f"<li>{i}</li>" for i in r.key_insights) + "</ul></div>")
    parts.append("</div></body></html>")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return output_path

def export_markdown(result: AnalysisResult, output_path: str, title: str = "Folder Analysis") -> str:
    """Write a Markdown report with tables and key insights."""
    r = result
    md: List[str] = []
    md.append(f"# {title}")
    md.append("")
    md.append(f"**Folder:** `{r.root_path}`  ")
    md.append(f"**Generated:** {r.generated_at} · **Duration:** {r.scan_duration_seconds}s")
    md.append("")
    md.append("## Summary")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Total files | {format_number(r.total_files)} |")
    md.append(f"| Directories | {format_number(r.total_directories)} |")
    md.append(f"| Total storage | {r.total_storage_formatted} |")
    md.append(f"| Average file size | {r.avg_file_size_formatted} |")
    md.append("")
    md.append("## File Types")
    md.append("")
    md.append("| # | Type | Category | Files | Storage | % |")
    md.append("|---|------|----------|------:|--------:|--:|")
    for i, d in enumerate(r.file_types[:r.config.top_n], 1):
        md.append(f"| {i} | `{d['label']}` | {d['category']} | "
                  f"{format_number(d['files'])} | {d['size_formatted']} | {d['percentage']}% |")
    md.append("| | **TOTAL** | | **{}** | **{}** | **100%** |".format(
        format_number(r.total_files), r.total_storage_formatted))
    md.append("")
    md.append("## Categories")
    md.append("")
    md.append("| Category | Files | Storage | % |")
    md.append("|----------|------:|--------:|--:|")
    for d in r.categories:
        md.append(f"| {d['name']} | {format_number(d['files'])} | "
                  f"{d['size_formatted']} | {d['percentage']}% |")
    md.append("")
    md.append("## Age Distribution")
    md.append("")
    md.append("| Age category | Files | Storage | % |")
    md.append("|--------------|------:|--------:|--:|")
    for d in r.age_distribution:
        md.append(f"| {d['category']} | {format_number(d['files'])} | "
                  f"{d['size_formatted']} | {d['percentage']}% |")
    md.append("")
    md.append("## Largest Files")
    md.append("")
    md.append("| # | Name | Type | Size | Location | Modified |")
    md.append("|---|------|------|-----:|----------|----------|")
    for i, f in enumerate(r.largest_files[:20], 1):
        md.append(f"| {i} | `{f['name']}` | {f['type']} | {f['size_formatted']} | "
                  f"`{f['parent']}` | {f['modified_formatted']} |")
    md.append("")
    if r.duplicate_groups:
        md.append("## Duplicate Files")
        md.append("")
        md.append(f"**Potential recovery:** {r.duplicate_wasted_formatted} "
                  f"across {len(r.duplicate_groups)} group(s)")
        md.append("")
        md.append("| Size | Copies | Wasted | Files |")
        md.append("|-----:|-------:|-------:|-------|")
        for g in r.duplicate_groups[:20]:
            names = ", ".join(f"`{Path(fx['path']).name}`" for fx in g["files"])
            md.append(f"| {g['size_formatted']} | {g['count']} | {g['wasted_formatted']} | {names} |")
        md.append("")
    md.append("## Key Insights")
    md.append("")
    for ins in r.key_insights:
        md.append(f"- {ins}")
    md.append("")
    md.append("## Directory Tree")
    md.append("")
    md.append("```\n" + r.tree_text + "\n```")
    md.append("")
    md.append(f"_Generated by Folder Storage Analytics Pro v{__import__('folder_analyzer').__version__}_")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    return output_path


def run_all_exports(result: AnalysisResult, output_dir: str, title: str = "Folder Analysis") -> List[str]:
    """Convenience: write every report format into ``output_dir``."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    return [
        export_txt(result, str(out / "SUMMARY.txt")),
        export_markdown(result, str(out / "REPORT.md"), title=title),
        export_json(result, str(out / "DATA.json")),
        export_csv(result, str(out / "DATA.csv")),
        export_html(result, str(out / "DASHBOARD.html"), title=title),
    ]

