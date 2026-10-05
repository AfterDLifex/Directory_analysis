"""
Export data formatting, templates, and export utilities.

Generates sleek, modern reports with glassmorphism aesthetics, responsive styling,
and vibrant SVG visualization charts.
"""

from __future__ import annotations

import csv
import dataclasses
import html as _html
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List

from .formats import format_number, format_size
from .models import AnalysisResult


def _esc(text: Any) -> str:
    """HTML-escape arbitrary text for safe embedding."""
    return _html.escape(str(text))


def _cosd(a: float) -> float:
    return math.cos(math.radians(a))


def _snd(a: float) -> float:
    return math.sin(math.radians(a))


def serialize_result(result: AnalysisResult) -> Dict[str, Any]:
    """Return a JSON-serialisable dictionary view of an AnalysisResult."""
    data = dataclasses.asdict(result)
    data["root_path"] = os.path.abspath(data["root_path"])
    return data


def export_json(result: AnalysisResult, output_path: str) -> str:
    """Write the full analysis as structured, pretty-printed JSON."""
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
        writer.writerow({
            "type": "TOTAL", "label": "", "category": "",
            "files": format_number(result.total_files),
            "size": result.total_storage,
            "size_formatted": result.total_storage_formatted,
            "percentage": 100.0,
        })
    return output_path


def export_txt(result: AnalysisResult, output_path: str) -> str:
    """Write a clean, readable plain-text summary."""
    r = result
    lines: List[str] = [
        "╔═══════════════════════════════════════════════════════════════════╗",
        "║            FOLDER ANALYSIS PRO — EXECUTIVE SUMMARY                ║",
        "╚═══════════════════════════════════════════════════════════════════╝",
        f"Folder    : {r.root_path}",
        f"Timestamp : {r.generated_at}",
        f"Duration  : {r.scan_duration_seconds}s",
        "",
        "► CORE METRICS",
        f"  • Total Files       : {format_number(r.total_files)}",
        f"  • Total Directories : {format_number(r.total_directories)}",
        f"  • Total Storage     : {r.total_storage_formatted}",
        f"  • Average File Size : {r.avg_file_size_formatted}",
    ]
    if r.duplicate_groups:
        lines.append(f"  • Duplicate Waste   : {r.duplicate_wasted_formatted} across {len(r.duplicate_groups)} groups")
    lines.append("")

    def block(title, rows, fmt):
        lines.append(f"► {title.upper()}")
        lines.append("-" * 65)
        for row in rows:
            lines.append(fmt(row))
        lines.append("")

    block(f"File Types (Top {r.config.top_n})", r.file_types,
          lambda d: f"  {d['label']:<18} {d['files']:>8} files  {d['size_formatted']:>12}  ({d['percentage']}%)")
    block("Categories", r.categories,
          lambda d: f"  {d['name']:<18} {d['files']:>8} files  {d['size_formatted']:>12}  ({d['percentage']}%)")
    block("Age Distribution", r.age_distribution,
          lambda d: f"  {d['category']:<22} {d['files']:>8} files  {d['size_formatted']:>12}  ({d['percentage']}%)")
    block("Size Distribution", r.size_distribution,
          lambda d: f"  {d['range']:<20} {d['count']:>8} files  ({d['percentage']}%)")

    if r.duplicate_groups:
        lines.append("► DUPLICATE FILES SUMMARY")
        lines.append("-" * 65)
        for g in r.duplicate_groups[:10]:
            lines.append(f"  • {g['count']} copies of {g['size_formatted']} (wasted {g['wasted_formatted']}):")
            for f in g["files"][:3]:
                lines.append(f"      - {Path(f['path']).name} in {f.get('parent', '')}")
        lines.append("")

    lines.append("► KEY INSIGHTS")
    lines.append("-" * 65)
    for ins in r.key_insights:
        lines.append(f"  ✓ {ins.replace('**', '')}")
    lines.append("")

    if r.warnings:
        lines.append("► WARNINGS & NOTICES")
        lines.append("-" * 65)
        for w in r.warnings:
            lines.append(f"  ! {w}")
        lines.append("")

    if r.tree_text:
        lines.append("► DIRECTORY HIERARCHY")
        lines.append("-" * 65)
        lines.append(r.tree_text)
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return output_path


def _svg_donut(data: List[Dict[str, Any]], size: int = 260, label: str = "") -> str:
    """Build a modern glassmorphic SVG donut chart with subtle glow."""
    if not data:
        return f'<svg width="{size}" height="{size}"></svg>'
    total = sum(max(d.get("size", 0), d.get("count", 0)) for d in data) or 1
    cx, cy, r = size / 2, size / 2, size / 2 - 32
    inner = r * 0.48
    strokes = []
    badges = []
    start_a = 0.0
    for d in data:
        val = max(d.get("size", 0), d.get("count", 0))
        pct = val / total
        end_a = start_a + pct * 360
        large = 1 if pct > 0.5 else 0
        sweep = 1 if (end_a - start_a) <= 180 else 0
        x1 = cx + r * _cosd(start_a)
        y1 = cy + r * _snd(start_a)
        x2 = cx + r * _cosd(end_a)
        y2 = cy + r * _snd(end_a)
        color = d.get("color", "#4f8cff")
        strokes.append(
            f'<path d="M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large} {sweep} {x2:.2f} {y2:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{inner}" opacity="0.9" '
            f'stroke-linecap="round"/>'
        )
        lbl = d.get("label") or d.get("category") or d.get("range") or d.get("name", "?")
        badges.append(
            f'<span class="badge"><span class="badge-dot" style="background:{color}"></span>'
            f'{_esc(lbl)} <b style="color:#ffffff;margin-left:4px">{pct*100:.1f}%</b></span>'
        )
        start_a = end_a

    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{cx}" cy="{cy}" r="{r + 10}" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r - inner/2}" fill="rgba(15,22,36,0.95)"/>'
        + "".join(strokes) +
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" '
        f'fill="#94a3b8" font-size="11" font-weight="600" text-transform="uppercase" letter-spacing="1">DISTRIBUTION</text>'
        f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" '
        f'fill="#ffffff" font-size="14" font-weight="bold">{_esc(label)}</text>'
        f'</svg>'
    )
    legend = '<div class="legend-wrap">' + "".join(badges) + "</div>"
    return f'<div class="donut-container">{svg}{legend}</div>'


def _svg_bar(data: List[Dict[str, Any]], width: int = 500, height: int = 280) -> str:
    """Build a modern horizontal glassmorphic bar chart with glowing bars."""
    if not data:
        return f'<svg width="{width}" height="{height}"></svg>'
    max_val = max((d.get("size", 0) or d.get("count", 0)) for d in data) or 1
    bar_h = 24
    gap = 10
    y = 36
    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" rx="12" fill="rgba(15,22,36,0.6)" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>',
    ]
    for d in data:
        val = d.get("size", 0) or d.get("count", 0)
        usable_w = width - 170
        w = max(4.0, (val / max_val) * usable_w)
        lbl = d.get("name") or d.get("label") or d.get("category") or d.get("range", "?")
        color = d.get("color", "#4f8cff")
        
        # Track background
        parts.append(
            f'<rect x="14" y="{y}" width="{usable_w}" height="{bar_h}" rx="6" fill="rgba(255,255,255,0.04)"/>'
        )
        # Value fill bar
        parts.append(
            f'<rect x="14" y="{y}" width="{w:.1f}" height="{bar_h}" rx="6" fill="{color}" opacity="0.85"/>'
        )
        # Label on bar
        parts.append(
            f'<text x="24" y="{y + bar_h/2 + 4}" font-size="11" font-weight="600" fill="#ffffff">{_esc(lbl)}</text>'
        )
        # Metric at right
        val_str = format_size(val) if "size" in d else format_number(val)
        parts.append(
            f'<text x="{width - 16}" y="{y + bar_h/2 + 4}" text-anchor="end" font-size="12" font-weight="700" fill="#93c5fd">{val_str}</text>'
        )
        y += bar_h + gap
    parts.append("</svg>")
    return "".join(parts)


def _html_table(rows: List[Dict[str, Any]], cols: List[str], headers=None) -> str:
    """Render a styled glassmorphic table."""
    head = headers or cols
    cells = "".join(f"<th>{_esc(h)}</th>" for h in head)
    body = []
    for row in rows:
        tds = "".join(f"<td>{_esc(row.get(c, ''))}</td>" for c in cols)
        body.append(f"<tr>{tds}</tr>")
    return (
        '<div class="table-container"><table class="glass-table"><thead><tr>' + cells + "</tr></thead><tbody>"
        + "".join(body) + "</tbody></table></div>"
    )


def _summary_cards(r: AnalysisResult) -> str:
    cards_data = [
        ("TOTAL FILES", format_number(r.total_files), f"{r.empty_files_count} empty files", "#3b82f6"),
        ("FOLDERS", format_number(r.total_directories), "Hierarchies", "#8b5cf6"),
        ("STORAGE", r.total_storage_formatted, "Total disk footprint", "#06b6d4"),
        ("AVG FILE SIZE", r.avg_file_size_formatted, "Calculated mean", "#10b981"),
        ("STORAGE HEALTH", f"{r.storage_efficiency_score}/100", r.storage_health_label, "#22c55e" if r.storage_efficiency_score >= 80 else "#eab308" if r.storage_efficiency_score >= 60 else "#ef4444"),
    ]
    if r.actionable_savings_bytes > 0:
        cards_data.append(("POTENTIAL RECOVERY", r.actionable_savings_formatted, f"{len(r.duplicate_groups)} duplicate clusters", "#f97316"))
    elif r.duplicate_groups:
        cards_data.append(("DUPLICATE WASTE", r.duplicate_wasted_formatted, f"{len(r.duplicate_groups)} duplicate clusters", "#ef4444"))
    
    html = []
    for title, val, sub, color in cards_data:
        html.append(f"""
        <div class="stat-card" style="--accent: {color}">
            <div class="stat-label">{title}</div>
            <div class="stat-val">{val}</div>
            <div class="stat-sub">{sub}</div>
        </div>
        """)
    return "".join(html)


def export_html(result: AnalysisResult, output_path: str, title: str = "Folder Analysis") -> str:
    """Write an ultra-sleek, self-contained, offline HTML dashboard with glassmorphism."""
    r = result
    css = """
    :root {
        --bg-grad: linear-gradient(135deg, #090d16 0%, #0d1424 50%, #080d17 100%);
        --glass-bg: rgba(18, 26, 44, 0.65);
        --glass-border: rgba(255, 255, 255, 0.08);
        --glass-border-bright: rgba(110, 168, 254, 0.25);
        --accent-glow: rgba(59, 130, 246, 0.25);
    }
    * { box-sizing: border-box; }
    body {
        margin: 0;
        background: var(--bg-grad);
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        min-height: 100vh;
        padding-bottom: 50px;
    }
    .wrapper {
        max-width: 1200px;
        margin: 0 auto;
        padding: 32px 24px;
    }
    .header {
        background: rgba(15, 22, 38, 0.75);
        border: 1px solid var(--glass-border);
        border-radius: 18px;
        padding: 24px 30px;
        margin-bottom: 26px;
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    .header h1 {
        margin: 0 0 6px;
        font-size: 26px;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #93c5fd 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .header-sub {
        color: #7b8ba5;
        font-size: 13px;
    }
    .badge-live {
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        border: 1px solid rgba(96, 165, 250, 0.4);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .cards-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 26px;
    }
    .stat-card {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        padding: 20px 22px;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        border-color: var(--glass-border-bright);
    }
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; width: 4px; height: 100%;
        background: var(--accent);
    }
    .stat-label {
        font-size: 11px;
        font-weight: 700;
        color: #8da2c0;
        letter-spacing: 0.08em;
    }
    .stat-val {
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        margin: 6px 0 2px;
    }
    .stat-sub {
        font-size: 12px;
        color: #64748b;
    }
    .grid2 {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
        gap: 22px;
        margin-bottom: 26px;
    }
    .glass-panel {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 18px;
        padding: 24px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }
    .glass-panel h2 {
        margin: 0 0 18px;
        font-size: 16px;
        font-weight: 700;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 10px;
        letter-spacing: 0.02em;
    }
    .donut-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .legend-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
        margin-top: 14px;
    }
    .badge {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 11px;
        display: inline-flex;
        align-items: center;
    }
    .badge-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }
    .table-container {
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .glass-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        text-align: left;
    }
    .glass-table th {
        background: rgba(14, 20, 34, 0.95);
        color: #8da2c0;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 10px 14px;
        border-bottom: 1px solid var(--glass-border);
    }
    .glass-table td {
        padding: 10px 14px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        color: #cbd5e1;
    }
    .glass-table tr:hover td {
        background: rgba(255,255,255,0.03);
        color: #ffffff;
    }
    .tree-box {
        background: rgba(10, 15, 26, 0.9);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        padding: 16px;
        font-family: 'SFMono-Regular', Consolas, Monaco, monospace;
        font-size: 12px;
        color: #93c5fd;
        white-space: pre-wrap;
        overflow-x: auto;
        line-height: 1.5;
    }
    .insight-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .insight-item {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
        font-size: 13px;
        line-height: 1.5;
    }
    .warn-badge {
        color: #f87171;
        font-weight: 600;
    }
    """
    parts = [
        "<!doctype html><html lang=en><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        f"<title>{_esc(title)} — Executive Report</title><style>{css}</style></head><body>",
        "<div class=wrapper>",
        "<div class=header>",
        "<div>",
        f"<h1>{_esc(title)}</h1>",
        f"<div class=header-sub>{_esc(r.root_path)} · Scanned in {r.scan_duration_seconds}s · Generated {_esc(r.generated_at)}</div>",
        "</div>",
        "<div class=badge-live>Enterprise Report</div>",
        "</div>",
        f'<div class=cards-row>{_summary_cards(r)}</div>',
        '<div class="grid2">',
        f'<div class="glass-panel"><h2>Storage by File Type</h2>{_svg_donut(r.file_types[:8], label="file types")}</div>',
        f'<div class="glass-panel"><h2>Storage by Category</h2>{_svg_donut(r.categories, label="categories")}</div>',
        "</div>",
        f'<div class="glass-panel" style="margin-bottom:26px"><h2>Top Directories (Largest Size)</h2>{_svg_bar(r.top_directories[:10], width=1100, height=320)}</div>',
        '<div class="grid2">',
        f'<div class="glass-panel"><h2>Age Distribution</h2>{_svg_bar(r.age_distribution, width=540, height=260)}</div>',
        f'<div class="glass-panel"><h2>Size Distribution</h2>{_svg_bar(r.size_distribution, width=540, height=260)}</div>',
        "</div>",
        '<div class="glass-panel" style="margin-bottom:26px"><h2>Extension Breakdown</h2>' + _html_table(
            r.file_types[:20], ["label", "category", "files", "size_formatted", "percentage"],
            headers=["Extension", "Category", "Files", "Storage", "% Share"]) + "</div>",
        '<div class="glass-panel" style="margin-bottom:26px"><h2>Largest Files Discovered</h2>' + _html_table(
            r.largest_files[:15], ["name", "parent", "type", "size_formatted", "modified_formatted"],
            headers=["File Name", "Location", "Type", "Size", "Modified"]) + "</div>",
    ]
    if r.duplicate_groups:
        parts.append(f'<div class="glass-panel" style="margin-bottom:26px"><h2>Duplicate Storage Clusters (<span class=warn-badge>Wasted {_esc(r.duplicate_wasted_formatted)}</span>)</h2>')
        for g in r.duplicate_groups[:12]:
            names = ", ".join(Path(f["path"]).name for f in g["files"])
            parts.append(
                f'<div class="insight-item">'
                f'<b>{format_number(g["count"])} copies</b> · {_esc(g["size_formatted"])} each '
                f'· <span class=warn-badge>Wasted: {_esc(g["wasted_formatted"])}</span><br>'
                f'<span style="color:#8da2c0;font-size:12px;margin-top:4px;display:inline-block">{_esc(names)}</span>'
                f'</div>'
            )
        parts.append("</div>")

    if r.actionable_recommendations:
        parts.append('<div class="glass-panel" style="margin-bottom:26px"><h2>Actionable Optimization Recommendations</h2>')
        for rec in r.actionable_recommendations:
            badge_color = "#ef4444" if rec["type"] == "Critical" else "#f59e0b" if rec["type"] == "Warning" else "#3b82f6"
            parts.append(
                f'<div class="insight-item" style="border-left: 4px solid {badge_color};">'
                f'<div style="font-weight:700;color:#ffffff;margin-bottom:4px;">'
                f'<span style="background:{badge_color};color:#ffffff;padding:2px 8px;border-radius:4px;font-size:11px;margin-right:8px;">{_esc(rec["type"])}</span>'
                f'{_esc(rec["title"])}</div>'
                f'<div style="color:#cbd5e1;font-size:12px;">{_esc(rec["action"])}</div>'
                f'</div>'
            )
        parts.append('</div>')

    parts.append('<div class="grid2">')
    parts.append('<div class="glass-panel"><h2>Key Insights</h2><ul class=insight-list>'
                 + "".join(f'<li class="insight-item">✓ {i}</li>' for i in r.key_insights) + "</ul></div>")
    parts.append('<div class="glass-panel"><h2>Directory Structure (Top Level)</h2><pre class=tree-box>'
                 + _esc(r.tree_text or "No hierarchy text available") + "</pre></div>")
    parts.append('</div>')

    parts.append("</div></body></html>")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return output_path


def export_markdown(result: AnalysisResult, output_path: str, title: str = "Folder Analysis") -> str:
    """Write an executive Markdown report with tables and diagnostics."""
    r = result
    md: List[str] = [
        f"# {title} — Executive Storage Report",
        "",
        f"> **Location:** `{r.root_path}`  ",
        f"> **Timestamp:** {r.generated_at} · **Scan Duration:** {r.scan_duration_seconds}s  ",
        f"> **Total Assets:** {format_number(r.total_files)} files across {format_number(r.total_directories)} directories ({r.total_storage_formatted})",
        "",
        "## Executive Summary",
        "",
        "| Metric | Value | Status |",
        "|:-------|:------|:-------|",
        f"| **Total Files** | {format_number(r.total_files)} | Indexed ({r.empty_files_count} empty files) |",
        f"| **Directories** | {format_number(r.total_directories)} | Scanned |",
        f"| **Total Disk Footprint** | **{r.total_storage_formatted}** | Complete |",
        f"| **Average File Size** | {r.avg_file_size_formatted} | Mean |",
        f"| **Storage Health Score** | **{r.storage_efficiency_score}/100** | {r.storage_health_label} |",
    ]
    if r.actionable_savings_bytes > 0:
        md.append(f"| **Potential Storage Recovery** | **{r.actionable_savings_formatted}** | {len(r.duplicate_groups)} duplicate clusters |")
    elif r.duplicate_groups:
        md.append(f"| **Duplicate Waste** | **{r.duplicate_wasted_formatted}** | {len(r.duplicate_groups)} duplicate clusters |")
    md.extend([
        "",
        "---",
        "",
        "## 📁 File Types Breakdown",
        "",
        "| Rank | Extension | Category | Files | Total Storage | Share |",
        "|:----:|:----------|:---------|------:|--------------:|------:|",
    ])
    for i, d in enumerate(r.file_types[:r.config.top_n], 1):
        md.append(f"| {i} | `{d['label']}` | {d['category']} | {format_number(d['files'])} | {d['size_formatted']} | {d['percentage']}% |")
    md.extend([
        "",
        "---",
        "",
        "## 🗂 Storage by Category",
        "",
        "| Category | Files Count | Aggregate Size | % of Total |",
        "|:---------|------------:|---------------:|-----------:|",
    ])
    for d in r.categories:
        md.append(f"| {d['name']} | {format_number(d['files'])} | {d['size_formatted']} | {d['percentage']}% |")

    md.extend([
        "",
        "---",
        "",
        "## 🕒 Age Distribution",
        "",
        "| Age Bracket | Files Count | Aggregate Size | Share |",
        "|:------------|------------:|---------------:|------:|",
    ])
    for d in r.age_distribution:
        md.append(f"| {d['category']} | {format_number(d['files'])} | {d['size_formatted']} | {d['percentage']}% |")

    md.extend([
        "",
        "---",
        "",
        "## Largest Files",
        "",
        "| # | File Name | Type | Size | Parent Directory | Last Modified |",
        "|---|---|---|---|---|---|",
    ])
    for i, f in enumerate(r.largest_files[:25], 1):
        md.append(f"| {i} | `{f['name']}` | {f['type']} | **{f['size_formatted']}** | `{f['parent']}` | {f['modified_formatted']} |")

    if r.duplicate_groups:
        md.extend([
            "",
            "---",
            "",
            "## ⚠️ Duplicate Files Analysis",
            "",
            f"**Recoverable Storage:** `{r.duplicate_wasted_formatted}` across **{len(r.duplicate_groups)}** duplicate clusters.",
            "",
            "| Individual Size | Redundant Copies | Total Space Wasted | Matching Files Sample |",
            "|----------------:|:----------------:|-------------------:|:----------------------|",
        ])
        for g in r.duplicate_groups[:20]:
            names = ", ".join(f"`{Path(fx['path']).name}`" for fx in g["files"][:3])
            md.append(f"| {g['size_formatted']} | {g['count']} | **{g['wasted_formatted']}** | {names} |")

    if r.actionable_recommendations:
        md.extend([
            "",
            "---",
            "",
            "## 🎯 Actionable Optimization Recommendations",
            "",
        ])
        for rec in r.actionable_recommendations:
            md.append(f"### [{rec['type']}] {rec['title']}")
            md.append(f"> {rec['action']}")
            md.append("")

    md.extend([
        "",
        "---",
        "",
        "## Key Insights & Observations",
        "",
    ])
    for ins in r.key_insights:
        md.append(f"- ✓ {ins}")

    if r.tree_text:
        md.extend([
            "",
            "## 🌳 Directory Tree Structure",
            "",
            "```",
            r.tree_text,
            "```",
        ])

    md.extend([
        "",
        f"_Generated automatically by Folder Storage Analytics Pro v{__import__('folder_analyzer').__version__}_",
    ])

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
