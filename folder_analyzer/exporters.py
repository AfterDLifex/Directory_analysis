"""
Export data formatting, templates, and export utilities.

Generates sleek, modern reports with glassmorphism aesthetics, responsive styling,
and vibrant animated SVG visualization charts.
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


# ---------------------------------------------------------------------------
# Presentation helpers (animated SVG + tables + cards)
# ---------------------------------------------------------------------------

def _svg_donut(data: List[Dict[str, Any]], size: int = 260, label: str = "") -> str:
    """Glassmorphic donut chart with draw-on-scroll animation."""
    if not data:
        return (
            f'<div class="empty-state" style="width:{size}px;height:{size}px">'
            'No data to display</div>'
        )

    total = sum(max(d.get("size", 0), d.get("count", 0)) for d in data) or 1
    cx, cy, r = size / 2, size / 2, size / 2 - 32
    inner = r * 0.48

    strokes, badges = [], []
    start_a = 0.0
    for i, d in enumerate(data):
        val = max(d.get("size", 0), d.get("count", 0))
        pct = val / total
        end_a = start_a + pct * 360
        large = 1 if (end_a - start_a) > 180 else 0

        if pct > 0.0005:
            x1 = cx + r * _cosd(start_a)
            y1 = cy + r * _snd(start_a)
            x2 = cx + r * _cosd(end_a)
            y2 = cy + r * _snd(end_a)
            color = d.get("color", "#4f8cff")
            strokes.append(
                f'<path class="donut-seg" style="--delay:{i * 0.10:.2f}s" '
                f'd="M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large} 1 '
                f'{x2:.2f} {y2:.2f}" '
                f'fill="none" stroke="{color}" stroke-width="{inner:.1f}" '
                f'opacity="0.92" stroke-linecap="butt" pathLength="1"/>'
            )

        lbl = (d.get("label") or d.get("category") or d.get("range")
               or d.get("name", "?"))
        color = d.get("color", "#4f8cff")
        badges.append(
            f'<span class="badge" style="--dot:{color}">'
            f'<span class="badge-dot"></span>{_esc(lbl)} '
            f'<b>{pct * 100:.1f}%</b></span>'
        )
        start_a = end_a

    svg = (
        f'<svg class="donut-svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{cx}" cy="{cy}" r="{r + 10}" fill="none" '
        f'stroke="rgba(255,255,255,0.05)" stroke-width="1"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r - inner / 2:.1f}" '
        f'fill="rgba(10,16,28,0.95)"/>'
        + "".join(strokes) +
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" '
        f'fill="#94a3b8" font-size="11" font-weight="600" '
        f'letter-spacing="1">DISTRIBUTION</text>'
        f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" '
        f'fill="#ffffff" font-size="14" font-weight="700">{_esc(label)}</text>'
        f'</svg>'
    )
    return ('<div class="donut-container">' + svg
            + '<div class="legend-wrap">' + "".join(badges) + '</div></div>')


def _svg_bar(data: List[Dict[str, Any]], width: int = 500,
             height: int = 280) -> str:
    """Horizontal glass bar chart with staggered grow animation."""
    if not data:
        return (f'<div class="empty-state" style="width:100%;height:{height}px">'
                'No data to display</div>')

    max_val = max((d.get("size", 0) or d.get("count", 0)) for d in data) or 1
    bar_h, gap, y0 = 24, 10, 36
    usable_w = width - 170

    parts = [
        f'<svg class="chart-svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" rx="12" '
        f'fill="rgba(10,16,28,0.55)" stroke="rgba(255,255,255,0.05)"/>',
    ]

    y = y0
    for i, d in enumerate(data):
        val = d.get("size", 0) or d.get("count", 0)
        w = max(4.0, (val / max_val) * usable_w)
        lbl = (d.get("name") or d.get("label") or d.get("category")
               or d.get("range", "?"))
        color = d.get("color", "#4f8cff")
        delay = i * 0.06

        # Track background
        parts.append(
            f'<rect x="14" y="{y}" width="{usable_w}" height="{bar_h}" '
            f'rx="6" fill="rgba(255,255,255,0.04)"/>'
        )
        # Animated fill bar
        parts.append(
            f'<rect class="bar-fill" style="--delay:{delay:.2f}s" '
            f'x="14" y="{y}" width="{w:.1f}" height="{bar_h}" rx="6" '
            f'fill="{color}" opacity="0.9"/>'
        )
        # Label on bar
        parts.append(
            f'<text x="26" y="{y + bar_h / 2 + 4}" font-size="11" '
            f'font-weight="600" fill="#ffffff" pointer-events="none">'
            f'{_esc(lbl)}</text>'
        )
        # Value at right, fade-in
        val_str = format_size(val) if "size" in d else format_number(val)
        parts.append(
            f'<text class="bar-value" style="--delay:{delay + 0.35:.2f}s" '
            f'x="{width - 16}" y="{y + bar_h / 2 + 4}" text-anchor="end" '
            f'font-size="12" font-weight="700" fill="#93c5fd">'
            f'{val_str}</text>'
        )
        y += bar_h + gap

    parts.append("</svg>")
    return "".join(parts)


def _html_table(rows: List[Dict[str, Any]], cols: List[str],
                headers=None, searchable: bool = True) -> str:
    """Render a styled glassmorphic table with optional search + sort."""
    head = headers or cols
    cells = "".join(f"<th>{_esc(h)}</th>" for h in head)
    body = []
    for row in rows:
        tds = "".join(f"<td>{_esc(row.get(c, ''))}</td>" for c in cols)
        body.append(f"<tr>{tds}</tr>")

    toolbar = ""
    if searchable:
        toolbar = (
            '<div class="table-toolbar">'
            '<input class="table-search" type="search" '
            'placeholder="Filter rows…" aria-label="Filter table rows">'
            '<span class="table-hint">click a header to sort</span>'
            '</div>'
        )
    return (
        toolbar
        + '<div class="table-container"><table class="glass-table">'
          '<thead><tr>' + cells + '</tr></thead><tbody>'
        + "".join(body)
        + '</tbody></table></div>'
    )


def _summary_cards(r: AnalysisResult) -> str:
    """Render the top-row KPI cards with animated counters."""
    cards_data = [
        ("TOTAL FILES", format_number(r.total_files),
         f"{r.empty_files_count} empty files", "#3b82f6"),
        ("FOLDERS", format_number(r.total_directories),
         "Hierarchies", "#8b5cf6"),
        ("STORAGE", r.total_storage_formatted,
         "Total disk footprint", "#06b6d4"),
        ("AVG FILE SIZE", r.avg_file_size_formatted,
         "Calculated mean", "#10b981"),
        ("STORAGE HEALTH", f"{r.storage_efficiency_score}/100",
         r.storage_health_label,
         "#22c55e" if r.storage_efficiency_score >= 80
         else "#eab308" if r.storage_efficiency_score >= 60
         else "#ef4444"),
    ]
    if r.actionable_savings_bytes > 0:
        cards_data.append((
            "POTENTIAL RECOVERY", r.actionable_savings_formatted,
            f"{len(r.duplicate_groups)} duplicate clusters", "#f97316",
        ))
    elif r.duplicate_groups:
        cards_data.append((
            "DUPLICATE WASTE", r.duplicate_wasted_formatted,
            f"{len(r.duplicate_groups)} duplicate clusters", "#ef4444",
        ))

    out = []
    for title, val, sub, color in cards_data:
        out.append(
            f'<div class="stat-card" style="--accent:{color}">'
            f'<div class="stat-label">{_esc(title)}</div>'
            f'<div class="stat-val" data-display="{_esc(val)}">'
            f'{_esc(val)}</div>'
            f'<div class="stat-sub">{_esc(sub)}</div>'
            f'</div>'
        )
    return "".join(out)


# ---------------------------------------------------------------------------
# HTML export — CSS and JS are kept as plain (non-f) strings so that literal
# curly braces are preserved.
# ---------------------------------------------------------------------------

_CSS = r"""
:root {
  --bg-1:#090d16; --bg-2:#0d1424; --bg-3:#080d17;
  --glass-bg:rgba(18,26,44,0.65);
  --glass-strong:rgba(14,20,34,0.9);
  --border:rgba(255,255,255,0.08);
  --border-bright:rgba(110,168,254,0.35);
  --text:#e2e8f0; --text-dim:#8da2c0; --text-muted:#64748b;
  --accent:#3b82f6; --accent-2:#8b5cf6; --accent-3:#06b6d4;
  --shadow:0 10px 30px rgba(0,0,0,0.35);
  --radius:18px;
  --ease:cubic-bezier(0.22,1,0.36,1);
  color-scheme: dark;
}
html[data-theme="light"] {
  --bg-1:#f4f7fc; --bg-2:#e9eff8; --bg-3:#f7f9fc;
  --glass-bg:rgba(255,255,255,0.8);
  --glass-strong:rgba(248,250,252,0.95);
  --border:rgba(15,22,38,0.08);
  --border-bright:rgba(59,130,246,0.35);
  --text:#0f172a; --text-dim:#475569; --text-muted:#64748b;
  --shadow:0 10px 30px rgba(15,22,38,0.08);
  color-scheme: light;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin:0; color:var(--text); min-height:100vh;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,
    Helvetica,Arial,sans-serif;
  background:linear-gradient(135deg,var(--bg-1) 0%,var(--bg-2) 50%,var(--bg-3) 100%);
  background-attachment:fixed;
  padding-bottom:80px;
  overflow-x:hidden;
}
a { color:inherit; }

/* Reading-progress bar */
.progress-bar {
  position:fixed; top:0; left:0; height:3px; width:0%;
  background:linear-gradient(90deg,#3b82f6,#8b5cf6,#06b6d4);
  z-index:100; transition:width .1s linear;
  box-shadow:0 0 12px rgba(59,130,246,0.6);
}

/* Floating background orbs */
.bg-orbs {
  position:fixed; inset:0; z-index:-1; overflow:hidden; pointer-events:none;
}
.bg-orbs span {
  position:absolute; border-radius:50%; filter:blur(90px);
  opacity:.35; animation:float 26s ease-in-out infinite;
}
.bg-orbs span:nth-child(1){
  width:520px;height:520px; top:-12%; left:-10%;
  background:radial-gradient(circle,#3b82f6,transparent 70%);
  animation-duration:28s;
}
.bg-orbs span:nth-child(2){
  width:460px;height:460px; top:32%; right:-12%;
  background:radial-gradient(circle,#8b5cf6,transparent 70%);
  animation-duration:34s; animation-delay:-9s;
}
.bg-orbs span:nth-child(3){
  width:400px;height:400px; bottom:-14%; left:28%;
  background:radial-gradient(circle,#06b6d4,transparent 70%);
  animation-duration:30s; animation-delay:-16s;
}
@keyframes float {
  0%,100% { transform:translate(0,0) scale(1); }
  33%     { transform:translate(60px,-50px) scale(1.12); }
  66%     { transform:translate(-40px,55px) scale(.94); }
}

/* Sticky top nav */
.topnav {
  position:sticky; top:0; z-index:50;
  backdrop-filter:blur(14px);
  background:color-mix(in srgb, var(--bg-1) 72%, transparent);
  border-bottom:1px solid var(--border);
}
.nav-inner {
  max-width:1200px; margin:0 auto; padding:10px 24px;
  display:flex; align-items:center; gap:20px;
}
.nav-brand {
  font-weight:800; font-size:14px; letter-spacing:.02em;
  background:linear-gradient(135deg,#93c5fd,#c4b5fd);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  white-space:nowrap;
}
.nav-links {
  list-style:none; padding:0; margin:0; display:flex; gap:4px;
  flex:1; overflow-x:auto; scrollbar-width:none;
}
.nav-links::-webkit-scrollbar { display:none; }
.nav-links a {
  display:inline-block; padding:8px 12px; border-radius:10px;
  font-size:13px; font-weight:600; color:var(--text-dim);
  text-decoration:none; transition:all .2s var(--ease);
  white-space:nowrap;
}
.nav-links a:hover {
  color:var(--text); background:rgba(255,255,255,0.06);
}
.nav-actions { display:flex; gap:6px; }
.nav-actions button {
  width:36px; height:36px; border-radius:10px; cursor:pointer;
  background:rgba(255,255,255,0.05); color:var(--text);
  border:1px solid var(--border); font-size:15px;
  transition:all .2s var(--ease);
}
.nav-actions button:hover {
  background:rgba(255,255,255,0.1); border-color:var(--border-bright);
  transform:translateY(-1px);
}

/* Layout wrapper */
.wrapper { max-width:1200px; margin:0 auto; padding:32px 24px; }

/* Scroll reveal */
.reveal {
  opacity:0; transform:translateY(18px);
  transition:opacity .7s var(--ease), transform .7s var(--ease);
  will-change:opacity, transform;
}
.reveal.in-view { opacity:1; transform:none; }

/* Header banner */
.header {
  background:var(--glass-bg);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:26px 32px;
  margin-bottom:26px;
  backdrop-filter:blur(14px);
  box-shadow:var(--shadow);
  display:flex; justify-content:space-between; align-items:center;
  flex-wrap:wrap; gap:16px;
  position:relative; overflow:hidden;
}
.header::after {
  content:''; position:absolute; inset:0;
  background:radial-gradient(600px circle at 0% 0%,
    rgba(59,130,246,0.15), transparent 55%);
  pointer-events:none;
}
.header h1 {
  margin:0 0 8px; font-size:28px; font-weight:800;
  background:linear-gradient(135deg,#ffffff 0%,#93c5fd 45%,#c4b5fd 100%);
  background-size:220% 220%;
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  animation:shimmer 8s ease-in-out infinite;
}
@keyframes shimmer {
  0%,100% { background-position:0% 50%; }
  50%     { background-position:100% 50%; }
}
.header-sub {
  color:var(--text-dim); font-size:13px;
  display:flex; align-items:center; gap:10px; flex-wrap:wrap;
}
.copy-path {
  background:rgba(255,255,255,0.05);
  border:1px solid var(--border);
  padding:3px 10px; border-radius:6px;
  cursor:pointer; transition:all .15s var(--ease);
  color:var(--text-dim); font-size:12px; font-family:inherit;
  display:inline-flex; align-items:center; gap:6px;
  max-width:60ch; overflow:hidden; text-overflow:ellipsis;
  white-space:nowrap;
}
.copy-path:hover { color:var(--text); border-color:var(--border-bright); }
.copy-path.copied { color:#22c55e; border-color:#22c55e; }
.badge-live {
  background:linear-gradient(135deg,
    rgba(59,130,246,0.22), rgba(139,92,246,0.22));
  color:#93c5fd; border:1px solid rgba(96,165,250,0.4);
  padding:6px 14px; border-radius:20px;
  font-size:11px; font-weight:800; letter-spacing:.08em;
  text-transform:uppercase;
  box-shadow:0 0 22px rgba(59,130,246,0.25);
}

/* Stat cards */
.cards-row {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:16px; margin-bottom:26px;
}
.stat-card {
  background:var(--glass-bg);
  border:1px solid var(--border);
  border-radius:16px;
  padding:20px 22px;
  position:relative; overflow:hidden;
  backdrop-filter:blur(10px);
  transition:transform .25s var(--ease), border-color .25s var(--ease),
             box-shadow .25s var(--ease);
}
.stat-card:hover {
  transform:translateY(-3px);
  border-color:var(--border-bright);
  box-shadow:0 14px 40px rgba(0,0,0,0.35),
             0 0 24px var(--accent-glow, rgba(59,130,246,0.2));
}
.stat-card::before {
  content:''; position:absolute;
  top:0; left:0; width:4px; height:100%;
  background:var(--accent);
  box-shadow:0 0 14px var(--accent);
}
.stat-label {
  font-size:11px; font-weight:800; color:var(--text-dim);
  letter-spacing:.1em; text-transform:uppercase;
}
.stat-val {
  font-size:28px; font-weight:800; color:var(--text);
  margin:8px 0 4px; letter-spacing:-.01em;
  font-variant-numeric:tabular-nums;
}
.stat-sub { font-size:12px; color:var(--text-muted); }

/* Panels */
.grid2 {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(460px,1fr));
  gap:22px; margin-bottom:26px;
}
.glass-panel {
  background:var(--glass-bg);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:24px;
  backdrop-filter:blur(12px);
  box-shadow:var(--shadow);
  margin-bottom:22px;
  transition:border-color .25s var(--ease),
             box-shadow .25s var(--ease);
}
.glass-panel:hover { border-color:var(--border-bright); }
.glass-panel h2 {
  margin:0 0 18px; font-size:16px; font-weight:700; color:var(--text);
  display:flex; align-items:center; gap:10px;
  cursor:pointer; user-select:none;
}
.glass-panel h2::before {
  content:''; width:8px; height:8px; border-radius:50%;
  background:linear-gradient(135deg,#60a5fa,#a78bfa);
  box-shadow:0 0 12px rgba(96,165,250,0.8);
}
.glass-panel h2::after {
  content:'▾'; margin-left:auto; font-size:12px;
  color:var(--text-muted);
  transition:transform .25s var(--ease);
}
.glass-panel.collapsed h2::after { transform:rotate(-90deg); }
.glass-panel.collapsed > *:not(h2) { display:none; }

/* Donut */
.donut-container {
  display:flex; flex-direction:column; align-items:center; justify-content:center;
}
.donut-seg {
  stroke-dasharray:1 1;
  stroke-dashoffset:1;
  animation:drawSeg 1.4s var(--ease) forwards;
  animation-delay:var(--delay,0s);
  filter:drop-shadow(0 0 6px currentColor);
}
@keyframes drawSeg { to { stroke-dashoffset:0; } }

/* Bars */
.bar-fill {
  transform:scaleX(0);
  transform-origin:left center;
  transform-box:fill-box;
  animation:growBar 1.1s var(--ease) forwards;
  animation-delay:var(--delay,0s);
}
@keyframes growBar { to { transform:scaleX(1); } }
.bar-value {
  opacity:0;
  animation:fadeVal .6s var(--ease) forwards;
  animation-delay:var(--delay,0s);
}
@keyframes fadeVal { to { opacity:1; } }

/* Legend */
.legend-wrap {
  display:flex; flex-wrap:wrap; gap:8px;
  justify-content:center; margin-top:14px;
}
.badge {
  background:rgba(255,255,255,0.05);
  border:1px solid var(--border);
  border-radius:8px; padding:5px 10px; font-size:11px;
  display:inline-flex; align-items:center; gap:6px;
  transition:all .2s var(--ease);
}
.badge:hover {
  border-color:var(--border-bright); transform:translateY(-1px);
}
.badge b { color:var(--text); font-weight:700; }
.badge-dot {
  width:8px; height:8px; border-radius:50%;
  background:var(--dot,#4f8cff);
  box-shadow:0 0 8px var(--dot,#4f8cff);
}

/* Tables */
.table-toolbar {
  display:flex; align-items:center; gap:12px; margin-bottom:12px;
}
.table-search {
  flex:1; max-width:280px;
  background:rgba(255,255,255,0.05);
  border:1px solid var(--border);
  color:var(--text); border-radius:10px;
  padding:9px 12px; font-size:13px;
  outline:none; transition:all .2s var(--ease);
  font-family:inherit;
}
.table-search:focus {
  border-color:var(--border-bright);
  box-shadow:0 0 0 3px rgba(59,130,246,0.15);
}
.table-hint { font-size:11px; color:var(--text-muted); }
.table-container {
  overflow-x:auto; border-radius:12px;
  border:1px solid var(--border);
}
.glass-table {
  width:100%; border-collapse:collapse; font-size:13px; text-align:left;
}
.glass-table th {
  background:var(--glass-strong);
  color:var(--text-dim); font-size:11px; font-weight:700;
  text-transform:uppercase; letter-spacing:.06em;
  padding:11px 14px; border-bottom:1px solid var(--border);
  position:sticky; top:0; z-index:1;
  white-space:nowrap;
}
.glass-table th.sortable { cursor:pointer; user-select:none; }
.glass-table th.sortable:hover { color:var(--text); }
.glass-table th[data-dir="asc"]::after  { content:' ▲'; color:#60a5fa; }
.glass-table th[data-dir="desc"]::after { content:' ▼'; color:#60a5fa; }
.glass-table td {
  padding:10px 14px; border-bottom:1px solid var(--border);
  color:var(--text); font-variant-numeric:tabular-nums;
}
.glass-table tbody tr { transition:background .15s var(--ease); }
.glass-table tbody tr:hover td { background:rgba(255,255,255,0.04); }
.glass-table tbody tr:last-child td { border-bottom:0; }

/* Tree */
.tree-box {
  background:var(--glass-strong);
  border:1px solid var(--border); border-radius:12px;
  padding:16px;
  font-family:'SFMono-Regular',Consolas,Monaco,monospace;
  font-size:12px; color:#93c5fd;
  white-space:pre-wrap; overflow-x:auto; line-height:1.55;
  max-height:420px;
}
html[data-theme="light"] .tree-box { color:#1d4ed8; }

/* Insights / recommendations */
.insight-list { list-style:none; padding:0; margin:0; }
.insight-item {
  background:rgba(255,255,255,0.03);
  border:1px solid var(--border);
  border-radius:10px;
  padding:12px 16px; margin-bottom:10px;
  font-size:13px; line-height:1.55;
  transition:all .2s var(--ease);
}
.insight-item:hover {
  background:rgba(255,255,255,0.055);
  border-color:var(--border-bright);
  transform:translateX(3px);
}
.warn-badge { color:#f87171; font-weight:700; }

/* Empty state */
.empty-state {
  display:flex; align-items:center; justify-content:center;
  border-radius:12px; border:1px dashed var(--border);
  color:var(--text-muted); font-size:13px; min-height:120px;
}

/* Back-to-top FAB */
.back-to-top {
  position:fixed; right:24px; bottom:24px;
  width:46px; height:46px; border-radius:50%;
  background:linear-gradient(135deg,#3b82f6,#8b5cf6);
  color:#fff; border:0; cursor:pointer;
  font-size:20px; font-weight:700;
  box-shadow:0 12px 32px rgba(59,130,246,0.4);
  opacity:0; transform:translateY(20px) scale(.9);
  pointer-events:none;
  transition:all .3s var(--ease);
  z-index:60;
}
.back-to-top.visible {
  opacity:1; transform:translateY(0) scale(1);
  pointer-events:auto;
}
.back-to-top:hover { transform:translateY(-3px) scale(1.05); }

/* Responsive */
@media (max-width:720px) {
  .wrapper { padding:20px 16px; }
  .header { padding:20px; }
  .header h1 { font-size:22px; }
  .stat-val { font-size:22px; }
  .grid2 { grid-template-columns:1fr; }
  .nav-links { display:none; }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration:.001ms !important;
    animation-iteration-count:1 !important;
    transition-duration:.001ms !important;
    scroll-behavior:auto !important;
  }
  .donut-seg { stroke-dashoffset:0 !important; }
  .bar-fill  { transform:scaleX(1) !important; }
  .reveal    { opacity:1 !important; transform:none !important; }
}

/* Print */
@media print {
  .topnav, .back-to-top, .progress-bar, .bg-orbs,
  .table-toolbar, .nav-actions { display:none !important; }
  body { background:#fff !important; color:#0f172a !important; }
  .glass-panel, .stat-card, .header {
    background:#fff !important; border:1px solid #cbd5e1 !important;
    box-shadow:none !important; break-inside:avoid;
  }
  .stat-val, .header h1 { -webkit-text-fill-color:#0f172a !important;
    background:none !important; color:#0f172a !important; }
  .tree-box { color:#1e293b !important; }
}
"""

_JS = r"""
(function(){
  'use strict';

  /* Progress bar */
  var pb = document.getElementById('progressBar');
  function updateProgress(){
    var h = document.documentElement;
    var pct = (h.scrollTop || document.body.scrollTop) /
      Math.max(1, (h.scrollHeight - h.clientHeight)) * 100;
    if (pb) pb.style.width = pct + '%';
  }
  window.addEventListener('scroll', updateProgress, {passive:true});
  updateProgress();

  /* Reveal on scroll */
  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if (e.isIntersecting){
        e.target.classList.add('in-view');
        io.unobserve(e.target);
      }
    });
  }, {threshold: 0.08, rootMargin: '0px 0px -40px 0px'});
  document.querySelectorAll('.reveal').forEach(function(el){ io.observe(el); });

  /* Counter animation */
  var reduce = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function animateCounter(el){
    var display = el.getAttribute('data-display') || el.textContent;
    var m = display.match(/^([\d,]+(?:\.\d+)?)(.*)$/);
    if (!m) return;
    var target = parseFloat(m[1].replace(/,/g,''));
    if (!isFinite(target) || target === 0){ el.textContent = display; return; }
    var decimals = (m[1].split('.')[1] || '').length;
    var suffix = m[2] || '';
    if (reduce){ el.textContent = display; return; }

    var start = performance.now();
    var dur = 1400;
    function tick(now){
      var t = Math.min((now - start) / dur, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      var v = target * eased;
      el.textContent = v.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      }) + suffix;
      if (t < 1) requestAnimationFrame(tick);
      else el.textContent = display;
    }
    requestAnimationFrame(tick);
  }

  var cio = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if (e.isIntersecting){
        animateCounter(e.target);
        cio.unobserve(e.target);
      }
    });
  }, {threshold: 0.35});
  document.querySelectorAll('.stat-val[data-display]')
    .forEach(function(el){ cio.observe(el); });

  /* Back to top */
  var top = document.getElementById('backToTop');
  if (top){
    window.addEventListener('scroll', function(){
      top.classList.toggle('visible', window.scrollY > 400);
    }, {passive:true});
    top.addEventListener('click', function(){
      window.scrollTo({top:0, behavior:'smooth'});
    });
  }

  /* Theme toggle */
  var themeBtn = document.getElementById('themeToggle');
  try {
    var saved = localStorage.getItem('fa-theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
  } catch(e){}
  if (themeBtn){
    themeBtn.addEventListener('click', function(){
      var cur = document.documentElement.getAttribute('data-theme') || 'dark';
      var next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('fa-theme', next); } catch(e){}
    });
  }

  /* Collapsible panels */
  document.querySelectorAll('.glass-panel h2').forEach(function(h){
    h.setAttribute('title', 'Click to collapse / expand');
    h.addEventListener('click', function(){
      h.parentElement.classList.toggle('collapsed');
    });
  });

  /* Table search */
  document.querySelectorAll('.table-search').forEach(function(input){
    input.addEventListener('input', function(){
      var q = input.value.toLowerCase();
      var panel = input.closest('.glass-panel') || document;
      panel.querySelectorAll('tbody tr').forEach(function(tr){
        tr.style.display =
          tr.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
      });
    });
  });

  /* Table sort */
  document.querySelectorAll('.glass-table').forEach(function(table){
    var ths = table.querySelectorAll('thead th');
    ths.forEach(function(th, idx){
      th.classList.add('sortable');
      th.addEventListener('click', function(){
        var tbody = table.querySelector('tbody');
        var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
        var dir = th.getAttribute('data-dir') === 'asc' ? 'desc' : 'asc';
        ths.forEach(function(o){ o.removeAttribute('data-dir'); });
        th.setAttribute('data-dir', dir);

        rows.sort(function(a, b){
          var av = (a.children[idx] && a.children[idx].textContent || '').trim();
          var bv = (b.children[idx] && b.children[idx].textContent || '').trim();
          var an = parseFloat(av.replace(/[^\d.\-]/g, ''));
          var bn = parseFloat(bv.replace(/[^\d.\-]/g, ''));
          if (!isNaN(an) && !isNaN(bn)){
            return dir === 'asc' ? an - bn : bn - an;
          }
          return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
        });
        rows.forEach(function(r){ tbody.appendChild(r); });
      });
    });
  });

  /* Copy-to-clipboard */
  document.querySelectorAll('[data-copy]').forEach(function(el){
    el.addEventListener('click', function(e){
      e.stopPropagation();
      var text = el.getAttribute('data-copy');
      var prev = el.getAttribute('data-prev') || el.textContent;
      var done = function(){
        el.classList.add('copied');
        el.setAttribute('data-prev', prev);
        el.textContent = '✓ Copied';
        setTimeout(function(){
          el.classList.remove('copied');
          el.textContent = prev;
        }, 1200);
      };
      if (navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(text).then(done).catch(done);
      } else { done(); }
    });
  });
})();
"""


def export_html(result: AnalysisResult, output_path: str,
                title: str = "Folder Analysis") -> str:
    """Write an ultra-sleek, self-contained, animated HTML dashboard."""
    r = result

    # --- Header ----------------------------------------------------------
    header = (
        '<div class="header reveal">'
        '<div>'
        f'<h1>{_esc(title)}</h1>'
        '<div class="header-sub">'
        f'<button class="copy-path" data-copy="{_esc(r.root_path)}" '
        f'title="Copy path to clipboard">📁 {_esc(r.root_path)}</button>'
        f'<span>· {r.scan_duration_seconds}s scan</span>'
        f'<span>· {_esc(r.generated_at)}</span>'
        '</div>'
        '</div>'
        '<div class="badge-live">Enterprise Report</div>'
        '</div>'
    )

    # --- Charts ----------------------------------------------------------
    chart_grid = (
        '<div class="grid2 reveal">'
        f'<div class="glass-panel"><h2>Storage by File Type</h2>'
        f'{_svg_donut(r.file_types[:8], label="file types")}</div>'
        f'<div class="glass-panel"><h2>Storage by Category</h2>'
        f'{_svg_donut(r.categories, label="categories")}</div>'
        '</div>'
    )

    top_dirs = (
        '<div class="glass-panel reveal"><h2>Top Directories (Largest Size)</h2>'
        f'{_svg_bar(r.top_directories[:10], width=1100, height=320)}</div>'
    )

    dists = (
        '<div class="grid2 reveal">'
        f'<div class="glass-panel"><h2>Age Distribution</h2>'
        f'{_svg_bar(r.age_distribution, width=540, height=260)}</div>'
        f'<div class="glass-panel"><h2>Size Distribution</h2>'
        f'{_svg_bar(r.size_distribution, width=540, height=260)}</div>'
        '</div>'
    )

    # --- Tables ----------------------------------------------------------
    ext_table = (
        '<div class="glass-panel reveal"><h2>Extension Breakdown</h2>'
        + _html_table(
            r.file_types[:20],
            ["label", "category", "files", "size_formatted", "percentage"],
            headers=["Extension", "Category", "Files", "Storage", "% Share"],
        )
        + '</div>'
    )
    files_table = (
        '<div class="glass-panel reveal"><h2>Largest Files Discovered</h2>'
        + _html_table(
            r.largest_files[:15],
            ["name", "parent", "type", "size_formatted", "modified_formatted"],
            headers=["File Name", "Location", "Type", "Size", "Modified"],
        )
        + '</div>'
    )

    # --- Duplicates ------------------------------------------------------
    dup_html = ""
    if r.duplicate_groups:
        rows = []
        for g in r.duplicate_groups[:12]:
            names = ", ".join(Path(f["path"]).name for f in g["files"])
            rows.append(
                f'<div class="insight-item">'
                f'<b>{format_number(g["count"])} copies</b> · '
                f'{_esc(g["size_formatted"])} each · '
                f'<span class="warn-badge">Wasted: '
                f'{_esc(g["wasted_formatted"])}</span><br>'
                f'<span style="color:var(--text-dim);font-size:12px;">'
                f'{_esc(names)}</span></div>'
            )
        dup_html = (
            '<div class="glass-panel reveal"><h2>Duplicate Storage Clusters '
            f'(<span class="warn-badge">Wasted '
            f'{_esc(r.duplicate_wasted_formatted)}</span>)</h2>'
            + "".join(rows) + '</div>'
        )

    # --- Recommendations -------------------------------------------------
    rec_html = ""
    if r.actionable_recommendations:
        items = []
        for rec in r.actionable_recommendations:
            color = ("#ef4444" if rec["type"] == "Critical"
                     else "#f59e0b" if rec["type"] == "Warning"
                     else "#3b82f6")
            items.append(
                f'<div class="insight-item" style="border-left:4px solid {color}">'
                f'<div style="font-weight:700;color:var(--text);margin-bottom:4px">'
                f'<span style="background:{color};color:#fff;padding:2px 8px;'
                f'border-radius:4px;font-size:11px;margin-right:8px">'
                f'{_esc(rec["type"])}</span>{_esc(rec["title"])}</div>'
                f'<div style="color:var(--text-dim);font-size:12px">'
                f'{_esc(rec["action"])}</div></div>'
            )
        rec_html = (
            '<div class="glass-panel reveal"><h2>Actionable Optimization '
            'Recommendations</h2>' + "".join(items) + '</div>'
        )

    # --- Insights + tree -------------------------------------------------
    insights = (
        '<div class="grid2 reveal">'
        '<div class="glass-panel"><h2>Key Insights</h2>'
        '<ul class="insight-list">'
        + "".join(f'<li class="insight-item">✓ {i}</li>' for i in r.key_insights)
        + '</ul></div>'
        '<div class="glass-panel"><h2>Directory Structure (Top Level)</h2>'
        '<pre class="tree-box">'
        + _esc(r.tree_text or "No hierarchy text available")
        + '</pre></div>'
        '</div>'
    )

    # --- Navigation ------------------------------------------------------
    nav = (
        '<nav class="topnav"><div class="nav-inner">'
        '<div class="nav-brand">📊 Folder Analysis</div>'
        '<ul class="nav-links">'
        '<li><a href="#overview">Overview</a></li>'
        '<li><a href="#charts">Charts</a></li>'
        '<li><a href="#breakdown">Breakdown</a></li>'
        '<li><a href="#duplicates">Duplicates</a></li>'
        '<li><a href="#recommendations">Actions</a></li>'
        '<li><a href="#insights">Insights</a></li>'
        '</ul>'
        '<div class="nav-actions">'
        '<button id="themeToggle" title="Toggle light / dark theme">🌓</button>'
        '<button onclick="window.print()" title="Print report">🖨</button>'
        '</div></div></nav>'
    )

    html_doc = (
        '<!doctype html><html lang="en" data-theme="dark"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{_esc(title)} — Executive Report</title>'
        f'<style>{_CSS}</style></head><body>'
        '<div class="progress-bar" id="progressBar"></div>'
        '<div class="bg-orbs" aria-hidden="true"><span></span><span></span>'
        '<span></span></div>'
        + nav
        + '<div class="wrapper">'
        + header
        + f'<section id="overview" class="cards-row reveal">'
          f'{_summary_cards(r)}</section>'
        + f'<section id="charts">{chart_grid}{top_dirs}{dists}</section>'
        + f'<section id="breakdown">{ext_table}{files_table}</section>'
        + f'<section id="duplicates">{dup_html}</section>'
        + f'<section id="recommendations">{rec_html}</section>'
        + f'<section id="insights">{insights}</section>'
        + '</div>'
        '<button id="backToTop" class="back-to-top" title="Back to top" '
        'aria-label="Back to top">↑</button>'
        f'<script>{_JS}</script>'
        '</body></html>'
    )

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html_doc)
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