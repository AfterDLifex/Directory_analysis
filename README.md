# Folder Analysis Pro

A modern, cross-platform desktop application for folder storage analytics —
built in Python with **PySide6 (Qt for Python)** and packaged into a single
standalone executable with **PyInstaller**.

Works on **Windows, macOS and Linux** with no system dependencies beyond the
bundled executable (or `python` + `pip install -r requirements.txt` when
running from source).

---

## Features

- **Modern dark UI** — sidebar navigation, stat cards, live charts (QtCharts),
  responsive layout; a single hand-written stylesheet so the look is identical
  on every OS.
- **Interactive analysis pages**
  - *Overview* — headline metrics (files, folders, storage, average size,
    duplicate waste) plus a file-type table.
  - *Charts* — donut charts for storage by file type and by category, bar
    charts for the largest directories, file-age and file-size distributions.
  - *Files* — largest and oldest files with type/size/location/modified.
  - *Duplicates* — hash-based duplicate detection with wasted-space totals.
  - *Insights* — automatically generated key findings plus a directory tree.
  - *Export* — write any combination of report formats to disk.
- **Self-contained reports** (no CDN / internet required to view them)
  - `DASHBOARD.html` — dark offline dashboard with inline SVG charts
  - `REPORT.md` — Markdown report with tables and insights
  - `DATA.json` — the complete result set for tooling
  - `DATA.csv` — file-type breakdown
  - `SUMMARY.txt` — compact plain-text summary
- **Headless CLI** — the same engine without a GUI, ideal for CI/SSH.
- **Cancellation & progress** — long scans run on a background thread and can
  be cancelled; the UI never freezes.

---

## Running from source

Requires Python 3.10+ (3.14 used for development).

```bash
pip install -r requirements.txt   # PySide6
python main.py                    # launch the GUI
```

### Headless CLI

```bash
python -m folder_analyzer --path "C:/Users/me/Documents" --formats all
python -m folder_analyzer --path ./data --formats html,json --output ./out
python -m folder_analyzer --help
```

---

## Building the executable

```bash
pip install pyinstaller
python build/build_app.py            # -> dist/FolderAnalysisPro(.exe)
```

Options: `--onedir` (faster-start folder build), `--console` (keep a console
window for debugging). A PyInstaller spec file is also provided:

```bash
pyinstaller build/folder_analysis.spec --noconfirm --clean
```

---

## Project layout

```
main.py                      GUI entry point
folder_analyzer/             reusable, GUI-free analysis engine
    models.py                dataclasses (FileInfo / AnalysisResult / AnalysisConfig)
    constants.py             categories, size/age buckets, palettes, icons
    formats.py               human formatting + streaming hashing
    scanner.py               cross-platform scandir walker (cancellable)
    analyzer.py              builds the full AnalysisResult
    exporters.py             HTML / Markdown / JSON / CSV / TXT reports
    cli.py / __main__.py     headless command-line interface
ui/                          PySide6 front end
    theme.py                 dark material palette + stylesheet
    scan_worker.py           background-thread scan worker (Qt signals)
    pages.py                 the six analysis pages
    main_window.py           window, navigation and threading wiring
build/
    build_app.py             cross-platform PyInstaller wrapper
    folder_analysis.spec     PyInstaller spec
```

The engine (`folder_analyzer/`) has **no Qt dependency**, so it can be reused
in other front-ends or scripts.

---

## Notes & limitations

- Duplicate detection hashes files up to `max_duplicate_size_mb` (default
  100 MB) to keep memory and runtime sane; larger files are skipped (with a
  warning) rather than hashed.
- Unreadable folders (permission errors) are skipped and reported in the
  warnings — a single bad subtree never aborts a scan.
- Hidden files follow each OS's convention (dot-prefixed on Unix,
  `FILE_ATTRIBUTE_HIDDEN` on Windows) and are excluded by default.

## License

MIT
