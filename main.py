#!/usr/bin/env python3
"""
Folder Storage Analytics Pro v2.0.0
====================================
A professional folder analysis tool with interactive HTML dashboards,
comprehensive reports, and multi-format exports.

Features:
- Interactive HTML dashboard with Chart.js (7 chart types)
- Professional Markdown reports with tables & insights
- JSON and CSV data exports
- Beautiful terminal output with color support
- Duplicate file detection with hash-based matching
- File age analysis (7 days to 1+ years)
- File size distribution analysis
- File category classification (Images, Videos, Documents, etc.)
- Directory depth analysis
- Configurable via config file or CLI arguments
- Multiple themes: Modern, Dark, Ocean, Sunset
- Multiple color palettes: Gradient, Vibrant, Pastel, Neon

Usage:
    python folder_analytics_pro.py --path "C:\\Users\\User\\Documents"
    python folder_analytics_pro.py --path "./data" --theme dark --detect-duplicates
    python folder_analytics_pro.py --config config.ini

Author: Your Name
Version: 2.0.0
License: MIT
"""

import os
import sys
import json
import csv
import shutil
import hashlib
import argparse
import configparser
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# ============================================================
# DEFAULT CONFIGURATION
# ============================================================

DEFAULT_CONFIG = {
    'folder_path': r"C:\Users\SENTIENTGEEKS\Downloads\sayan.das@sentientgeeks.com_1731\sayan.das@sentientgeeks.com_1731",
    'top_directories': 30,
    'top_file_types': 30,
    'output_dir_name': "folder_analysis",
    'readme_output': True,
    'readme_file_name': "FOLDER_ANALYTICS.md",
    'html_output': True,
    'html_file_name': "FOLDER_ANALYTICS_DASHBOARD.html",
    'json_output': True,
    'json_file_name': "FOLDER_ANALYTICS_DATA.json",
    'csv_output': True,
    'csv_file_name': "FOLDER_ANALYTICS_DATA.csv",
    'detect_duplicates': True,
    'max_duplicate_size_mb': 100,
    'include_hidden_files': False,
    'chart_theme': 'modern',
    'color_scheme': 'gradient',
    'enable_3d_charts': False,
    'show_file_age_analysis': True,
    'show_storage_trends': True,
    'max_json_files': 1000,
    'generate_tree_view': True,
    'tree_max_depth': 3,
    'export_pdf': False,
    'pdf_file_name': "FOLDER_ANALYTICS_REPORT.pdf",
}

# Fix for Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ============================================================
# COLOR THEMES
# ============================================================

THEMES = {
    'modern': {
        'primary': '#667eea',
        'secondary': '#764ba2',
        'accent': '#f093fb',
        'success': '#00d9ff',
        'warning': '#ff6b6b',
        'info': '#4facfe',
        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'card_bg': 'rgba(255, 255, 255, 0.95)',
        'text': '#2d3748',
        'text_light': '#718096',
    },
    'dark': {
        'primary': '#00d9ff',
        'secondary': '#00f5a0',
        'accent': '#ff6b6b',
        'success': '#00f5a0',
        'warning': '#ff6b6b',
        'info': '#00d9ff',
        'background': 'linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)',
        'card_bg': 'rgba(30, 41, 59, 0.95)',
        'text': '#e2e8f0',
        'text_light': '#94a3b8',
    },
    'ocean': {
        'primary': '#4facfe',
        'secondary': '#00f2fe',
        'accent': '#43e97b',
        'success': '#43e97b',
        'warning': '#fa709a',
        'info': '#4facfe',
        'background': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'card_bg': 'rgba(255, 255, 255, 0.95)',
        'text': '#1a365d',
        'text_light': '#4a5568',
    },
    'sunset': {
        'primary': '#fa709a',
        'secondary': '#fee140',
        'accent': '#ff6b6b',
        'success': '#43e97b',
        'warning': '#ff6b6b',
        'info': '#fa709a',
        'background': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
        'card_bg': 'rgba(255, 255, 255, 0.95)',
        'text': '#2d3748',
        'text_light': '#718096',
    }
}

COLOR_PALETTES = {
    'gradient': [
        '#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe',
        '#00f2fe', '#43e97b', '#38f9d7', '#fa709a', '#fee140',
        '#30cfd0', '#330867', '#a8edea', '#fed6e3', '#ff9a9e',
        '#fecfef', '#ffecd2', '#fcb69f', '#ff8a80', '#ea80fc',
    ],
    'vibrant': [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
        '#F8C471', '#82E0AA', '#F1948A', '#85929E', '#73C6B6',
        '#E59866', '#AF7AC5', '#5DADE2', '#58D68D', '#F4D03F',
    ],
    'pastel': [
        '#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF',
        '#E6E6FA', '#F0E68C', '#DDA0DD', '#98D8C8', '#F7DC6F',
        '#C1E1C1', '#F7DC6F', '#FFB6C1', '#87CEEB', '#D8BFD8',
        '#F5DEB3', '#FFE4E1', '#E0FFFF', '#FFFACD', '#F0FFF0',
    ],
    'neon': [
        '#FF00FF', '#00FFFF', '#FFFF00', '#FF00CC', '#00FF00',
        '#FF6600', '#CC00FF', '#00CCFF', '#FFCC00', '#00FFCC',
        '#FF0066', '#6600FF', '#00FF66', '#FF3300', '#9900FF',
        '#00FF99', '#FF9900', '#0099FF', '#FF0099', '#99FF00',
    ]
}

# ============================================================
# TERMINAL COLORS
# ============================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ============================================================
# HELPERS
# ============================================================

def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024:
            return f"{size:,.2f} {unit}"
        size /= 1024
    return f"{size:,.2f} PB"

def format_number(num: int) -> str:
    """Format large numbers with commas."""
    return f"{num:,}"

def get_file_type(file_path: Path) -> str:
    """Get file extension or [NO EXTENSION]."""
    extension = file_path.suffix.lower()
    if not extension:
        return "[NO EXTENSION]"
    return extension

def get_file_category(extension: str) -> str:
    """Categorize files by type."""
    categories = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.raw'],
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
        'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpeg'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso'],
        'code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.php', '.rb', '.go', '.rs', '.ts'],
        'data': ['.json', '.xml', '.csv', '.yaml', '.yml', '.sql', '.db', '.sqlite'],
        'executables': ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.app'],
    }
    ext_lower = extension.lower()
    for category, extensions in categories.items():
        if ext_lower in extensions:
            return category.title()
    return 'Other'

def get_color(index: int, palette: str = 'gradient') -> str:
    """Get consistent color from palette."""
    colors = COLOR_PALETTES.get(palette, COLOR_PALETTES['gradient'])
    return colors[index % len(colors)]

def get_file_icon(extension: str) -> str:
    """Get emoji icon for file type."""
    icons = {
        '.pdf': '📄', '.doc': '📝', '.docx': '📝', '.txt': '📃',
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🎨',
        '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬',
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵',
        '.zip': '📦', '.rar': '📦', '.7z': '📦',
        '.py': '🐍', '.js': '⚡', '.html': '🌐', '.css': '🎨',
        '.exe': '⚙️', '.msi': '⚙️',
        '.json': '📊', '.xml': '📊', '.csv': '📊',
    }
    return icons.get(extension.lower(), '📎')

def ensure_output_directory(base_path: Path, output_dir_name: str) -> Path:
    """Create output directory and return its path."""
    output_path = base_path / output_dir_name
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "charts").mkdir(exist_ok=True)
    (output_path / "data").mkdir(exist_ok=True)
    (output_path / "reports").mkdir(exist_ok=True)
    (output_path / "visualizations").mkdir(exist_ok=True)
    return output_path

def safe_print(text: str) -> None:
    """Safely print text that might contain emojis."""
    try:
        print(text)
    except UnicodeEncodeError:
        import re
        clean_text = re.sub(r'[^\x00-\x7F]+', '', text)
        print(clean_text)

def calculate_hash(file_path: Path, algorithm: str = 'md5', chunk_size: int = 8192) -> Optional[str]:
    """Calculate file hash for duplicate detection."""
    try:
        hasher = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None

def get_file_age_category(age_days: int) -> str:
    """Categorize file by age."""
    if age_days < 7:
        return 'Last 7 days'
    elif age_days < 30:
        return 'Last 30 days'
    elif age_days < 90:
        return 'Last 3 months'
    elif age_days < 180:
        return 'Last 6 months'
    elif age_days < 365:
        return 'Last year'
    else:
        return 'Over 1 year'

# ============================================================
# ANALYSIS ENGINE
# ============================================================

class FolderAnalyzer:
    """Professional folder analysis engine."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.root = Path(config['folder_path'])
        self.output_dir = None
        
        self.total_files = 0
        self.total_directories = 0
        self.total_storage = 0
        
        self.file_type_count = Counter()
        self.file_type_size = defaultdict(int)
        self.file_category_count = Counter()
        self.file_category_size = defaultdict(int)
        self.directory_file_count = Counter()
        self.directory_size = defaultdict(int)
        self.directory_depth_count = Counter()
        self.age_distribution = Counter()
        self.size_distribution = Counter()
        
        self.all_files: List[Dict[str, Any]] = []
        self.duplicate_files: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.largest_files: List[Dict[str, Any]] = []
        self.oldest_files: List[Dict[str, Any]] = []
        self.newest_files: List[Dict[str, Any]] = []
    
    def analyze(self) -> bool:
        """Run complete folder analysis."""
        if not self.root.exists():
            safe_print(f"{Colors.FAIL}ERROR: Folder does not exist.{Colors.ENDC}")
            return False
        if not self.root.is_dir():
            safe_print(f"{Colors.FAIL}ERROR: Path is not a directory.{Colors.ENDC}")
            return False
        
        safe_print(f"\n{Colors.GREEN}[+] Analyzing folder: {self.root.resolve()}{Colors.ENDC}")
        print("=" * 70)
        
        self.output_dir = ensure_output_directory(self.root, self.config['output_dir_name'])
        safe_print(f"{Colors.CYAN}[+] Output directory created: {self.output_dir}{Colors.ENDC}")
        
        print(f"{Colors.BLUE}[+] Scanning directory structure...{Colors.ENDC}")
        self._scan_directory()
        
        print(f"{Colors.BLUE}[+] Processing analysis data...{Colors.ENDC}")
        self._process_results()
        
        if self.config['detect_duplicates']:
            print(f"{Colors.BLUE}[+] Detecting duplicate files...{Colors.ENDC}")
            self._detect_duplicates()
        
        self._generate_outputs()
        self._print_terminal_summary()
        return True
    
    def _scan_directory(self) -> None:
        """Scan directory structure and collect file information."""
        current_time = datetime.now()
        max_duplicate_size = self.config['max_duplicate_size_mb'] * 1024 * 1024
        
        for current_path, directories, files in os.walk(self.root):
            current = Path(current_path)
            self.total_directories += len(directories)
            
            try:
                relative = current.relative_to(self.root)
                depth = len(relative.parts) if str(relative) != '.' else 0
            except ValueError:
                depth = 0
            
            self.directory_depth_count[depth] += 1
            
            try:
                relative = current.relative_to(self.root)
                top_directory = "[ROOT]" if len(relative.parts) == 0 else relative.parts[0]
            except ValueError:
                top_directory = "[ROOT]"
            
            for file_name in files:
                file_path = current / file_name
                
                if not self.config['include_hidden_files'] and file_name.startswith('.'):
                    continue
                
                try:
                    stat = file_path.stat()
                    size = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    age_days = (current_time - mtime).days
                except (PermissionError, OSError):
                    continue
                
                self.total_files += 1
                self.total_storage += size
                
                file_type = get_file_type(file_path)
                category = get_file_category(file_type)
                
                self.file_type_count[file_type] += 1
                self.file_type_size[file_type] += size
                self.file_category_count[category] += 1
                self.file_category_size[category] += size
                self.directory_file_count[top_directory] += 1
                self.directory_size[top_directory] += size
                
                age_category = get_file_age_category(age_days)
                self.age_distribution[age_category] += size
                
                if size < 1024:
                    size_cat = "< 1 KB"
                elif size < 1024 * 1024:
                    size_cat = "1 KB - 1 MB"
                elif size < 10 * 1024 * 1024:
                    size_cat = "1 MB - 10 MB"
                elif size < 100 * 1024 * 1024:
                    size_cat = "10 MB - 100 MB"
                elif size < 1024 * 1024 * 1024:
                    size_cat = "100 MB - 1 GB"
                else:
                    size_cat = "> 1 GB"
                self.size_distribution[size_cat] += 1
                
                file_info = {
                    'path': str(file_path),
                    'name': file_name,
                    'type': file_type,
                    'category': category,
                    'size': size,
                    'size_formatted': format_size(size),
                    'directory': top_directory,
                    'parent': str(current.relative_to(self.root)) if current != self.root else "[ROOT]",
                    'depth': depth,
                    'modified': mtime.isoformat(),
                    'modified_formatted': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                    'age_days': age_days,
                    'age_category': age_category,
                    'icon': get_file_icon(file_type),
                }
                
                if self.config['detect_duplicates'] and size <= max_duplicate_size and size > 0:
                    file_hash = calculate_hash(file_path)
                    if file_hash:
                        file_info['hash'] = file_hash
                        self.duplicate_files[file_hash].append(file_info)
                
                self.all_files.append(file_info)
        
        safe_print(f"{Colors.GREEN}[+] Found {format_number(self.total_files)} files in {format_number(self.total_directories)} directories{Colors.ENDC}")
        safe_print(f"{Colors.GREEN}[+] Total storage: {format_size(self.total_storage)}{Colors.ENDC}")
    
    def _process_results(self) -> None:
        """Process and sort analysis results."""
        self.largest_files = sorted(self.all_files, key=lambda x: x['size'], reverse=True)[:50]
        self.oldest_files = sorted(self.all_files, key=lambda x: x['age_days'], reverse=True)[:50]
        self.newest_files = sorted(self.all_files, key=lambda x: x['age_days'])[:50]
        self.duplicate_files = {k: v for k, v in self.duplicate_files.items() if len(v) > 1}
    
    def _detect_duplicates(self) -> None:
        """Detect and report duplicate files."""
        duplicate_count = len(self.duplicate_files)
        if duplicate_count > 0:
            total_duplicate_size = sum(
                files[0]['size'] * (len(files) - 1) 
                for files in self.duplicate_files.values()
            )
            safe_print(f"{Colors.WARNING}[!] Found {duplicate_count} duplicate groups, wasting {format_size(total_duplicate_size)}{Colors.ENDC}")
    
    def _generate_outputs(self) -> None:
        """Generate all output files."""
        if self.config['html_output']:
            print(f"{Colors.BLUE}[+] Generating HTML dashboard...{Colors.ENDC}")
            self._generate_html_dashboard()
        
        if self.config['json_output']:
            print(f"{Colors.BLUE}[+] Generating JSON data...{Colors.ENDC}")
            self._generate_json_data()
        
        if self.config['csv_output']:
            print(f"{Colors.BLUE}[+] Generating CSV data...{Colors.ENDC}")
            self._generate_csv_data()
        
        if self.config['readme_output']:
            print(f"{Colors.BLUE}[+] Generating Markdown report...{Colors.ENDC}")
            self._generate_markdown_report()
        
        print(f"{Colors.BLUE}[+] Generating summary text...{Colors.ENDC}")
        self._generate_summary_txt()
        
        if self.config['detect_duplicates'] and self.duplicate_files:
            print(f"{Colors.BLUE}[+] Generating duplicate report...{Colors.ENDC}")
            self._generate_duplicate_report()

    def _generate_html_dashboard(self) -> None:
        """Generate interactive HTML dashboard."""
        theme = THEMES.get(self.config['chart_theme'], THEMES['modern'])
        palette = self.config['color_scheme']
        
        file_type_data = self._get_top_file_types()
        directory_data = self._get_top_directories()
        category_data = self._get_category_data()
        age_data = self._get_age_data()
        size_data = self._get_size_distribution_data()
        
        file_type_labels = json.dumps([d['type'] for d in file_type_data])
        file_type_sizes = json.dumps([d['size'] for d in file_type_data])
        file_type_files = json.dumps([d['files'] for d in file_type_data])
        file_type_colors = json.dumps([get_color(i, palette) for i in range(len(file_type_data))])
        
        directory_labels = json.dumps([d['name'] for d in directory_data])
        directory_sizes = json.dumps([d['size'] for d in directory_data])
        directory_files = json.dumps([d['files'] for d in directory_data])
        directory_colors = json.dumps([get_color(i, palette) for i in range(len(directory_data))])
        
        category_labels = json.dumps([d['name'] for d in category_data])
        category_sizes = json.dumps([d['size'] for d in category_data])
        category_colors = json.dumps([get_color(i, palette) for i in range(len(category_data))])
        
        age_labels = json.dumps([d['category'] for d in age_data])
        age_sizes = json.dumps([d['size'] for d in age_data])
        age_colors = json.dumps([get_color(i, palette) for i in range(len(age_data))])
        
        size_labels = json.dumps([d['range'] for d in size_data])
        size_counts = json.dumps([d['count'] for d in size_data])
        size_colors = json.dumps([get_color(i, palette) for i in range(len(size_data))])
        
        duplicate_groups = len(self.duplicate_files)
        duplicate_wasted = sum(
            files[0]['size'] * (len(files) - 1) 
            for files in self.duplicate_files.values()
        ) if self.duplicate_files else 0
        
        top_files_html = self._generate_top_files_html()
        oldest_files_html = self._generate_oldest_files_html()
        
        root_path = str(self.root.resolve())
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_files_str = format_number(self.total_files)
        total_dirs_str = format_number(self.total_directories)
        total_storage_str = format_size(self.total_storage)
        avg_size = format_size(self.total_storage // self.total_files) if self.total_files > 0 else '0 B'
        max_depth = str(max(self.directory_depth_count.keys()) if self.directory_depth_count else 0)
        top_category = max(self.file_category_count.keys(), key=lambda x: self.file_category_count[x]) if self.file_category_count else 'N/A'
        
        # Build HTML using string formatting
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Folder Storage Analytics Pro - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: """ + theme['background'] + """;
            min-height: 100vh;
            padding: 20px;
            color: """ + theme['text'] + """;
        }
        .container { max-width: 1600px; margin: 0 auto; animation: fadeIn 0.8s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(40px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        @keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-10px); } }
        .header {
            background: """ + theme['card_bg'] + """;
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 25px 80px rgba(0,0,0,0.3);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.2);
            position: relative;
            overflow: hidden;
        }
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, """ + theme['primary'] + """40 0%, transparent 70%);
            animation: float 6s ease-in-out infinite;
        }
        .header h1 {
            font-size: 3em;
            font-weight: 800;
            background: linear-gradient(135deg, """ + theme['primary'] + """ 0%, """ + theme['secondary'] + """ 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
            position: relative;
        }
        .header .subtitle { color: """ + theme['text_light'] + """; font-size: 1.2em; font-weight: 400; position: relative; }
        .header .path {
            background: rgba(""" + theme['primary'].replace('#', '') + """, 0.1);
            padding: 15px 20px;
            border-radius: 12px;
            font-family: 'Courier New', monospace;
            margin-top: 15px;
            word-break: break-all;
            border-left: 4px solid """ + theme['primary'] + """;
            position: relative;
            font-size: 0.95em;
        }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card {
            background: """ + theme['card_bg'] + """;
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            animation: slideUp 0.6s ease-out;
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
            overflow: hidden;
        }
        .stat-card::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, """ + theme['primary'] + """, """ + theme['secondary'] + """);
            transform: scaleX(0);
            transition: transform 0.4s ease;
        }
        .stat-card:hover { transform: translateY(-8px) scale(1.02); box-shadow: 0 25px 60px rgba(0,0,0,0.3); }
        .stat-card:hover::after { transform: scaleX(1); }
        .stat-card .icon {
            font-size: 2.5em;
            margin-bottom: 15px;
            background: linear-gradient(135deg, """ + theme['primary'] + """, """ + theme['secondary'] + """);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-card .number {
            font-size: 2.8em;
            font-weight: 800;
            background: linear-gradient(135deg, """ + theme['primary'] + """ 0%, """ + theme['secondary'] + """ 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.2;
        }
        .stat-card .label { color: """ + theme['text_light'] + """; font-size: 1em; margin-top: 8px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; }
        .chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 25px; margin-bottom: 30px; }
        .chart-container {
            background: """ + theme['card_bg'] + """;
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
            animation: slideUp 0.8s ease-out;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s ease;
        }
        .chart-container:hover { transform: translateY(-3px); }
        .chart-container h2 { color: """ + theme['text'] + """; margin-bottom: 25px; font-size: 1.4em; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .chart-container h2 i { background: linear-gradient(135deg, """ + theme['primary'] + """, """ + theme['secondary'] + """); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .chart-wrapper { position: relative; height: 350px; }
        .full-width { grid-column: 1 / -1; }
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 25px; margin-bottom: 30px; }
        .info-card {
            background: """ + theme['card_bg'] + """;
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
            animation: slideUp 1s ease-out;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .info-card h2 { color: """ + theme['text'] + """; margin-bottom: 20px; font-size: 1.3em; font-weight: 700; display: flex; align-items: center; gap: 10px; }
        .info-card h2 i { background: linear-gradient(135deg, """ + theme['primary'] + """, """ + theme['secondary'] + """); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .file-list { list-style: none; max-height: 400px; overflow-y: auto; }
        .file-list::-webkit-scrollbar { width: 6px; }
        .file-list::-webkit-scrollbar-track { background: rgba(0,0,0,0.05); border-radius: 3px; }
        .file-list::-webkit-scrollbar-thumb { background: linear-gradient(135deg, """ + theme['primary'] + """, """ + theme['secondary'] + """); border-radius: 3px; }
        .file-item { display: flex; align-items: center; padding: 12px 15px; border-radius: 12px; margin-bottom: 8px; background: rgba(0,0,0,0.03); transition: all 0.3s ease; border-left: 3px solid transparent; }
        .file-item:hover { background: rgba(""" + theme['primary'].replace('#', '') + """, 0.1); border-left-color: """ + theme['primary'] + """; transform: translateX(5px); }
        .file-item .file-icon { font-size: 1.5em; margin-right: 12px; width: 30px; text-align: center; }
        .file-item .file-info { flex: 1; min-width: 0; }
        .file-item .file-name { font-weight: 600; color: """ + theme['text'] + """; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .file-item .file-path { font-size: 0.8em; color: """ + theme['text_light'] + """; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .file-item .file-size { font-weight: 700; color: """ + theme['primary'] + """; font-size: 0.95em; white-space: nowrap; }
        .badge { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 20px; font-size: 0.85em; font-weight: 600; margin: 5px; transition: all 0.3s ease; }
        .badge:hover { transform: scale(1.05); }
        .badge-success { background: rgba(0, 217, 255, 0.15); color: """ + theme['success'] + """; }
        .badge-info { background: rgba(79, 172, 254, 0.15); color: """ + theme['info'] + """; }
        .badge-warning { background: rgba(255, 107, 107, 0.15); color: """ + theme['warning'] + """; }
        .badge-primary { background: rgba(102, 126, 234, 0.15); color: """ + theme['primary'] + """; }
        .footer { text-align: center; color: rgba(255,255,255,0.7); padding: 30px; font-size: 0.95em; }
        .footer a { color: """ + theme['accent'] + """; text-decoration: none; font-weight: 600; }
        .duplicate-alert {
            background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(250, 112, 154, 0.1));
            border: 2px solid """ + theme['warning'] + """;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 15px;
            animation: pulse 2s ease-in-out infinite;
        }
        .duplicate-alert i { font-size: 2em; color: """ + theme['warning'] + """; }
        .duplicate-alert .alert-content h3 { color: """ + theme['warning'] + """; margin-bottom: 5px; }
        .duplicate-alert .alert-content p { color: """ + theme['text_light'] + """; }
        @media (max-width: 768px) {
            .chart-grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 2em; }
            .stat-card .number { font-size: 2em; }
            .container { padding: 10px; }
        }
        .progress-bar { width: 100%; height: 8px; background: rgba(0,0,0,0.1); border-radius: 4px; overflow: hidden; margin-top: 8px; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, """ + theme['primary'] + """, """ + theme['secondary'] + """); border-radius: 4px; transition: width 1s ease-out; }
        .stat-detail { display: flex; justify-content: space-between; margin-top: 10px; font-size: 0.85em; color: """ + theme['text_light'] + """; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-chart-pie"></i> Folder Storage Analytics Pro</h1>
            <div class="subtitle">Interactive Dashboard with Advanced Analytics & Visualizations</div>
            <div class="path"><i class="fas fa-folder-open"></i> """ + root_path + """</div>
            <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 10px;">
                <span class="badge badge-success"><i class="fas fa-calendar"></i> Generated: """ + now_str + """</span>
                <span class="badge badge-info"><i class="fas fa-hdd"></i> """ + total_storage_str + """ Total</span>
                <span class="badge badge-primary"><i class="fas fa-files"></i> """ + total_files_str + """ Files</span>
                <span class="badge badge-warning"><i class="fas fa-folder"></i> """ + total_dirs_str + """ Directories</span>
            </div>
        </div>
        """
        
        # Add duplicate alert if applicable
        if self.duplicate_files:
            html += """
        <div class="duplicate-alert">
            <i class="fas fa-exclamation-triangle"></i>
            <div class="alert-content">
                <h3>Duplicate Files Detected</h3>
                <p>Found """ + str(duplicate_groups) + """ groups of duplicate files wasting """ + format_size(duplicate_wasted) + """ of storage space.</p>
            </div>
        </div>
        """
        
        # Stats grid
        html += """
        <div class="stats-grid">
            <div class="stat-card" style="animation-delay: 0.1s;">
                <div class="icon"><i class="fas fa-file-alt"></i></div>
                <div class="number">""" + total_files_str + """</div>
                <div class="label">Total Files</div>
                <div class="progress-bar"><div class="progress-fill" style="width: 100%"></div></div>
                <div class="stat-detail"><span>Avg Size</span><span>""" + avg_size + """</span></div>
            </div>
            <div class="stat-card" style="animation-delay: 0.2s;">
                <div class="icon"><i class="fas fa-folder-tree"></i></div>
                <div class="number">""" + total_dirs_str + """</div>
                <div class="label">Total Directories</div>
                <div class="progress-bar"><div class="progress-fill" style="width: 80%"></div></div>
                <div class="stat-detail"><span>Max Depth</span><span>""" + max_depth + """ levels</span></div>
            </div>
            <div class="stat-card" style="animation-delay: 0.3s;">
                <div class="icon"><i class="fas fa-database"></i></div>
                <div class="number">""" + total_storage_str + """</div>
                <div class="label">Total Storage</div>
                <div class="progress-bar"><div class="progress-fill" style="width: 100%"></div></div>
                <div class="stat-detail"><span>File Types</span><span>""" + str(len(self.file_type_count)) + """ unique</span></div>
            </div>
            <div class="stat-card" style="animation-delay: 0.4s;">
                <div class="icon"><i class="fas fa-layer-group"></i></div>
                <div class="number">""" + str(len(self.file_category_count)) + """</div>
                <div class="label">Categories</div>
                <div class="progress-bar"><div class="progress-fill" style="width: 60%"></div></div>
                <div class="stat-detail"><span>Top Category</span><span>""" + top_category + """</span></div>
            </div>
        </div>
        """
        
        # Charts grid
        html += """
        <div class="chart-grid">
            <div class="chart-container">
                <h2><i class="fas fa-chart-pie"></i> File Type Distribution (by Size)</h2>
                <div class="chart-wrapper"><canvas id="fileTypeChart"></canvas></div>
            </div>
            <div class="chart-container">
                <h2><i class="fas fa-folder"></i> Directory Distribution (by Size)</h2>
                <div class="chart-wrapper"><canvas id="directoryChart"></canvas></div>
            </div>
            <div class="chart-container">
                <h2><i class="fas fa-chart-bar"></i> File Count by Type</h2>
                <div class="chart-wrapper"><canvas id="fileCountChart"></canvas></div>
            </div>
            <div class="chart-container">
                <h2><i class="fas fa-sitemap"></i> File Count by Directory</h2>
                <div class="chart-wrapper"><canvas id="directoryCountChart"></canvas></div>
            </div>
            <div class="chart-container">
                <h2><i class="fas fa-tags"></i> File Categories</h2>
                <div class="chart-wrapper"><canvas id="categoryChart"></canvas></div>
            </div>
            <div class="chart-container">
                <h2><i class="fas fa-clock"></i> File Age Distribution</h2>
                <div class="chart-wrapper"><canvas id="ageChart"></canvas></div>
            </div>
            <div class="chart-container full-width">
                <h2><i class="fas fa-ruler"></i> File Size Distribution</h2>
                <div class="chart-wrapper"><canvas id="sizeChart"></canvas></div>
            </div>
        </div>
        """
        
        # Info grid
        html += """
        <div class="info-grid">
            <div class="info-card">
                <h2><i class="fas fa-crown"></i> Largest Files</h2>
                <ul class="file-list">""" + top_files_html + """</ul>
            </div>
            <div class="info-card">
                <h2><i class="fas fa-hourglass-end"></i> Oldest Files</h2>
                <ul class="file-list">""" + oldest_files_html + """</ul>
            </div>
        </div>
        """
        
        # Footer
        html += """
        <div class="footer">
            <p><i class="fas fa-code"></i> Generated by <strong>Folder Storage Analytics Pro</strong> v2.0.0</p>
            <p style="margin-top: 10px; opacity: 0.7;">Data is current as of generation time - """ + now_str + """</p>
        </div>
    </div>
    """
        
        # JavaScript
        html += """
    <script>
        Chart.register(ChartDataLabels);
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: { size: 12, family: 'Inter' }
                    }
                },
                datalabels: {
                    color: '#fff',
                    font: { size: 11, weight: 'bold', family: 'Inter' },
                    formatter: function(value, context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        return (value / total * 100).toFixed(1) + '%';
                    }
                }
            }
        };
        
        new Chart(document.getElementById('fileTypeChart'), {
            type: 'doughnut',
            data: {
                labels: """ + file_type_labels + """,
                datasets: [{
                    data: """ + file_type_sizes + """,
                    backgroundColor: """ + file_type_colors + """,
                    borderWidth: 3,
                    borderColor: '#fff',
                    hoverOffset: 15
                }]
            },
            options: {
                ...commonOptions,
                cutout: '60%',
                plugins: {
                    ...commonOptions.plugins,
                    datalabels: {
                        ...commonOptions.plugins.datalabels,
                        anchor: 'end',
                        align: 'start',
                        offset: 10
                    }
                }
            }
        });
        
        new Chart(document.getElementById('directoryChart'), {
            type: 'doughnut',
            data: {
                labels: """ + directory_labels + """,
                datasets: [{
                    data: """ + directory_sizes + """,
                    backgroundColor: """ + directory_colors + """,
                    borderWidth: 3,
                    borderColor: '#fff',
                    hoverOffset: 15
                }]
            },
            options: {
                ...commonOptions,
                cutout: '50%'
            }
        });
        
        new Chart(document.getElementById('fileCountChart'), {
            type: 'bar',
            data: {
                labels: """ + file_type_labels + """,
                datasets: [{
                    label: 'File Count',
                    data: """ + file_type_files + """,
                    backgroundColor: """ + file_type_colors + """,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        color: '#333',
                        anchor: 'end',
                        align: 'top',
                        font: { size: 11, weight: 'bold' },
                        formatter: (value) => value.toLocaleString()
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: {
                            callback: (value) => value >= 1000 ? (value/1000).toFixed(1) + 'K' : value
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { maxRotation: 45, font: { size: 10 } }
                    }
                }
            }
        });
        
        new Chart(document.getElementById('directoryCountChart'), {
            type: 'bar',
            data: {
                labels: """ + directory_labels + """,
                datasets: [{
                    label: 'File Count',
                    data: """ + directory_files + """,
                    backgroundColor: """ + directory_colors + """,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        color: '#333',
                        anchor: 'end',
                        align: 'top',
                        font: { size: 11, weight: 'bold' },
                        formatter: (value) => value.toLocaleString()
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { maxRotation: 45, font: { size: 10 } }
                    }
                }
            }
        });
        
        new Chart(document.getElementById('categoryChart'), {
            type: 'polarArea',
            data: {
                labels: """ + category_labels + """,
                datasets: [{
                    data: """ + category_sizes + """,
                    backgroundColor: """ + category_colors + """,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    r: {
                        ticks: { display: false },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    }
                }
            }
        });
        
        new Chart(document.getElementById('ageChart'), {
            type: 'line',
            data: {
                labels: """ + age_labels + """,
                datasets: [{
                    label: 'Storage by Age',
                    data: """ + age_sizes + """,
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: '#667eea',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#667eea',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        color: '#667eea',
                        anchor: 'end',
                        align: 'top',
                        font: { size: 10, weight: 'bold' },
                        formatter: (value) => (value / 1024 / 1024 / 1024).toFixed(1) + ' GB'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: {
                            callback: (value) => (value / 1024 / 1024 / 1024).toFixed(1) + ' GB'
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
        
        new Chart(document.getElementById('sizeChart'), {
            type: 'bar',
            data: {
                labels: """ + size_labels + """,
                datasets: [{
                    label: 'Number of Files',
                    data: """ + size_counts + """,
                    backgroundColor: """ + size_colors + """,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        color: '#333',
                        anchor: 'end',
                        align: 'top',
                        font: { size: 12, weight: 'bold' },
                        formatter: (value) => value.toLocaleString()
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: {
                            callback: (value) => value >= 1000 ? (value/1000).toFixed(1) + 'K' : value
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    </script>
</body>
</html>
        """
        
        output_file = self.output_dir / "reports" / self.config['html_file_name']
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"   {Colors.GREEN}[+] HTML Dashboard: {output_file}{Colors.ENDC}")
        except OSError as error:
            print(f"   {Colors.FAIL}[!] ERROR: Could not create HTML report: {error}{Colors.ENDC}")
    
    def _generate_top_files_html(self) -> str:
        """Generate HTML for top files list."""
        html = []
        for file_info in self.largest_files[:15]:
            html.append('<li class="file-item"><span class="file-icon">' + file_info['icon'] + '</span><div class="file-info"><div class="file-name">' + file_info['name'] + '</div><div class="file-path">' + file_info['parent'] + '</div></div><span class="file-size">' + file_info['size_formatted'] + '</span></li>')
        return "\n".join(html)
    
    def _generate_oldest_files_html(self) -> str:
        """Generate HTML for oldest files list."""
        html = []
        for file_info in self.oldest_files[:15]:
            html.append('<li class="file-item"><span class="file-icon">' + file_info['icon'] + '</span><div class="file-info"><div class="file-name">' + file_info['name'] + '</div><div class="file-path">' + file_info['modified_formatted'] + ' - ' + str(file_info['age_days']) + ' days old</div></div><span class="file-size">' + file_info['size_formatted'] + '</span></li>')
        return "\n".join(html)

    def _generate_json_data(self) -> None:
        """Generate JSON data export."""
        json_data = {
            'metadata': {
                'version': '2.0.0',
                'generated_at': datetime.now().isoformat(),
                'root': str(self.root.resolve()),
                'output_directory': str(self.output_dir),
            },
            'summary': {
                'total_files': self.total_files,
                'total_directories': self.total_directories,
                'total_storage': self.total_storage,
                'total_storage_formatted': format_size(self.total_storage),
                'unique_file_types': len(self.file_type_count),
                'unique_categories': len(self.file_category_count),
                'max_depth': max(self.directory_depth_count.keys()) if self.directory_depth_count else 0,
            },
            'file_types': self._get_top_file_types(),
            'directories': self._get_top_directories(),
            'categories': self._get_category_data(),
            'age_distribution': self._get_age_data(),
            'size_distribution': self._get_size_distribution_data(),
            'depth_distribution': dict(self.directory_depth_count),
            'largest_files': self.largest_files[:50],
            'oldest_files': self.oldest_files[:50],
            'newest_files': self.newest_files[:50],
            'duplicates': {
                'groups_found': len(self.duplicate_files),
                'wasted_space': sum(f[0]['size'] * (len(f) - 1) for f in self.duplicate_files.values()) if self.duplicate_files else 0,
                'duplicate_groups': [
                    {
                        'hash': hash_val,
                        'file_count': len(files),
                        'file_size': files[0]['size'],
                        'file_size_formatted': files[0]['size_formatted'],
                        'total_wasted': files[0]['size'] * (len(files) - 1),
                        'files': files
                    }
                    for hash_val, files in list(self.duplicate_files.items())[:100]
                ]
            },
            'files': self.all_files[:self.config['max_json_files']],
        }
        
        output_file = self.output_dir / "data" / self.config['json_file_name']
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, default=str)
            print(f"   {Colors.GREEN}[+] JSON Data: {output_file}{Colors.ENDC}")
        except OSError as error:
            print(f"   {Colors.FAIL}[!] ERROR: Could not create JSON data: {error}{Colors.ENDC}")
    
    def _generate_csv_data(self) -> None:
        """Generate CSV data export."""
        output_file = self.output_dir / "data" / self.config['csv_file_name']
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if self.all_files:
                    fieldnames = ['name', 'type', 'category', 'size', 'size_formatted', 
                                'directory', 'parent', 'depth', 'modified', 'age_days', 
                                'age_category', 'path']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    # Filter to only include the fields we want
                    filtered_files = []
                    for file_info in self.all_files:
                        filtered = {k: v for k, v in file_info.items() if k in fieldnames}
                        filtered_files.append(filtered)
                    writer.writerows(filtered_files)
            print(f"   {Colors.GREEN}[+] CSV Data: {output_file}{Colors.ENDC}")
        except OSError as error:
            print(f"   {Colors.FAIL}[!] ERROR: Could not create CSV data: {error}{Colors.ENDC}")
    
    def _generate_markdown_report(self) -> None:
        """Generate comprehensive Markdown report with charts."""
        output_file = self.output_dir / self.config['readme_file_name']
        
        try:
            md = []
            
            md.append("# Folder Storage Analytics Pro")
            md.append("")
            md.append("> **Professional folder analysis with interactive visualizations**")
            md.append("")
            md.append("**Root:** `" + str(self.root.resolve()) + "`")
            md.append("**Generated:** " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            md.append("**Version:** 2.0.0")
            md.append("")
            
            md.append("## Quick Statistics")
            md.append("")
            md.append("| Metric | Value |")
            md.append("|--------|-------|")
            md.append("| **Total Files** | " + format_number(self.total_files) + " |")
            md.append("| **Total Directories** | " + format_number(self.total_directories) + " |")
            md.append("| **Total Storage** | " + format_size(self.total_storage) + " |")
            md.append("| **Unique File Types** | " + str(len(self.file_type_count)) + " |")
            md.append("| **File Categories** | " + str(len(self.file_category_count)) + " |")
            md.append("| **Average File Size** | " + (format_size(self.total_storage // self.total_files) if self.total_files > 0 else '0 B') + " |")
            md.append("| **Max Directory Depth** | " + str(max(self.directory_depth_count.keys()) if self.directory_depth_count else 0) + " levels |")
            md.append("")
            
            md.append("## Storage Overview")
            md.append("")
            total_gb = self.total_storage / (1024**3)
            used_bar = "█" * int((total_gb / 100) * 50) if total_gb < 100 else "█" * 50
            free_bar = "░" * (50 - len(used_bar))
            md.append("```")
            md.append("Total Storage: " + format_size(self.total_storage))
            md.append("[" + used_bar + free_bar + "] " + f"{total_gb:.1f}" + " GB")
            md.append("```")
            md.append("")
            
            md.append("## File Type Summary")
            md.append("")
            md.append("| # | File Type | Files | Storage | % of Storage | Category |")
            md.append("|---|-----------|------:|--------:|-------------:|----------|")
            
            file_type_data = self._get_top_file_types()
            for i, data in enumerate(file_type_data, 1):
                icon = get_file_icon(data['type'])
                md.append("| " + str(i) + " | " + icon + " `" + data['type'] + "` | " + format_number(data['files']) + " | " + data['size_formatted'] + " | " + f"{data['percentage']:.2f}" + "% | " + data.get('category', 'Other') + " |")
            
            md.append("| | **TOTAL** | **" + format_number(self.total_files) + "** | **" + format_size(self.total_storage) + "** | **100.00%** | |")
            md.append("")
            
            md.append("## Category Breakdown")
            md.append("")
            md.append("| Category | Files | Storage | % of Storage |")
            md.append("|----------|------:|--------:|-------------:|")
            
            category_data = self._get_category_data()
            for data in category_data:
                md.append("| " + data['name'] + " | " + format_number(data['files']) + " | " + data['size_formatted'] + " | " + f"{data['percentage']:.2f}" + "% |")
            
            md.append("")
            
            md.append("## Directory Summary")
            md.append("")
            md.append("| # | Directory | Files | Storage | % of Storage |")
            md.append("|---|-----------|------:|--------:|-------------:|")
            
            directory_data = self._get_top_directories()
            for i, data in enumerate(directory_data, 1):
                md.append("| " + str(i) + " | `" + data['name'] + "` | " + format_number(data['files']) + " | " + data['size_formatted'] + " | " + f"{data['percentage']:.2f}" + "% |")
            
            md.append("| | **TOTAL** | **" + format_number(self.total_files) + "** | **" + format_size(self.total_storage) + "** | **100.00%** |")
            md.append("")
            
            md.append("## File Age Distribution")
            md.append("")
            md.append("| Age Category | Storage | % of Storage |")
            md.append("|--------------|--------:|-------------:|")
            
            age_data = self._get_age_data()
            for data in age_data:
                md.append("| " + data['category'] + " | " + data['size_formatted'] + " | " + f"{data['percentage']:.2f}" + "% |")
            
            md.append("")
            
            md.append("## File Size Distribution")
            md.append("")
            md.append("| Size Range | File Count | % of Files |")
            md.append("|------------|----------:|-----------:|")
            
            size_data = self._get_size_distribution_data()
            for data in size_data:
                md.append("| " + data['range'] + " | " + format_number(data['count']) + " | " + f"{data['percentage']:.2f}" + "% |")
            
            md.append("")
            
            md.append("## Largest Files")
            md.append("")
            md.append("| # | Name | Type | Size | Location | Modified |")
            md.append("|---|------|------|------|----------|----------|")
            
            for i, file_info in enumerate(self.largest_files[:20], 1):
                md.append("| " + str(i) + " | `" + file_info['name'] + "` | " + file_info['type'] + " | " + file_info['size_formatted'] + " | `" + file_info['parent'] + "` | " + file_info['modified_formatted'] + " |")
            
            md.append("")
            
            md.append("## Oldest Files")
            md.append("")
            md.append("| # | Name | Type | Size | Age | Modified |")
            md.append("|---|------|------|------|-----|----------|")
            
            for i, file_info in enumerate(self.oldest_files[:20], 1):
                md.append("| " + str(i) + " | `" + file_info['name'] + "` | " + file_info['type'] + " | " + file_info['size_formatted'] + " | " + str(file_info['age_days']) + " days | " + file_info['modified_formatted'] + " |")
            
            md.append("")
            
            if self.duplicate_files:
                md.append("## Duplicate Files")
                md.append("")
                total_wasted = sum(f[0]['size'] * (len(f) - 1) for f in self.duplicate_files.values())
                md.append("> **" + str(len(self.duplicate_files)) + "** duplicate groups found, wasting **" + format_size(total_wasted) + "** of storage space.")
                md.append("")
                md.append("| Hash | Size | Count | Wasted Space | Files |")
                md.append("|------|------|------:|-------------:|-------|")
                
                for hash_val, files in list(self.duplicate_files.items())[:20]:
                    wasted = files[0]['size'] * (len(files) - 1)
                    file_names = ", ".join(["`" + f['name'] + "`" for f in files[:3]])
                    if len(files) > 3:
                        file_names += " (+" + str(len(files) - 3) + " more)"
                    md.append("| `" + hash_val[:16] + "...` | " + files[0]['size_formatted'] + " | " + str(len(files)) + " | " + format_size(wasted) + " | " + file_names + " |")
                
                md.append("")
            
            md.append("## Directory Depth Analysis")
            md.append("")
            md.append("| Depth Level | Directory Count |")
            md.append("|-------------|----------------:|")
            
            for depth, count in sorted(self.directory_depth_count.items()):
                md.append("| Level " + str(depth) + " | " + format_number(count) + " |")
            
            md.append("")
            
            md.append("## Key Insights")
            md.append("")
            
            insights = []
            if file_type_data:
                top_type = file_type_data[0]
                insights.append("- **" + top_type['type'] + "** files consume the most space at **" + top_type['size_formatted'] + "** (" + f"{top_type['percentage']:.1f}" + "% of total)")
            
            if directory_data:
                top_dir = directory_data[0]
                insights.append("- **" + top_dir['name'] + "** is the largest directory with **" + top_dir['size_formatted'] + "** (" + f"{top_dir['percentage']:.1f}" + "% of total)")
            
            if category_data:
                top_cat = category_data[0]
                insights.append("- **" + top_cat['name'] + "** is the dominant category with **" + top_cat['size_formatted'] + "** (" + f"{top_cat['percentage']:.1f}" + "% of total)")
            
            if age_data:
                oldest_age = max(age_data, key=lambda x: x['size'])
                insights.append("- Most storage is occupied by files **" + oldest_age['category'] + "** (" + oldest_age['size_formatted'] + ")")
            
            if self.duplicate_files:
                total_wasted = sum(f[0]['size'] * (len(f) - 1) for f in self.duplicate_files.values())
                insights.append("- **" + format_size(total_wasted) + "** could be saved by removing duplicate files")
            
            avg_size = self.total_storage // self.total_files if self.total_files > 0 else 0
            insights.append("- Average file size is **" + format_size(avg_size) + "**")
            
            for insight in insights:
                md.append(insight)
            
            md.append("")
            md.append("---")
            md.append("")
            md.append("*Generated by Folder Storage Analytics Pro v2.0.0*")
            md.append("*Analysis completed at " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*")
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(md))
            
            print(f"   {Colors.GREEN}[+] Markdown Report: {output_file}{Colors.ENDC}")
            
        except OSError as error:
            print(f"   {Colors.FAIL}[!] ERROR: Could not create markdown report: {error}{Colors.ENDC}")

    def _generate_summary_txt(self) -> None:
        """Generate enhanced plain text summary file."""
        output_file = self.output_dir / "SUMMARY.txt"
        
        try:
            lines = []
            lines.append("╔" + "═" * 78 + "╗")
            lines.append("║" + "FOLDER STORAGE ANALYTICS PRO".center(78) + "║")
            lines.append("║" + "Professional Analysis Report".center(78) + "║")
            lines.append("╚" + "═" * 78 + "╝")
            lines.append("")
            lines.append("  Root Path: " + str(self.root.resolve()))
            lines.append("  Generated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            lines.append("  Version:   2.0.0")
            lines.append("")
            lines.append("┌" + "─" * 78 + "┐")
            lines.append("│" + "SUMMARY STATISTICS".center(78) + "│")
            lines.append("├" + "─" * 78 + "┤")
            lines.append("│  Total Files          : " + format_number(self.total_files).rjust(58) + " │")
            lines.append("│  Total Directories    : " + format_number(self.total_directories).rjust(58) + " │")
            lines.append("│  Total Storage        : " + format_size(self.total_storage).rjust(58) + " │")
            lines.append("│  Unique File Types    : " + format_number(len(self.file_type_count)).rjust(58) + " │")
            lines.append("│  File Categories      : " + format_number(len(self.file_category_count)).rjust(58) + " │")
            lines.append("│  Average File Size    : " + (format_size(self.total_storage // self.total_files) if self.total_files > 0 else '0 B').rjust(58) + " │")
            lines.append("│  Max Directory Depth  : " + (str(max(self.directory_depth_count.keys()) if self.directory_depth_count else 0) + " levels").rjust(58) + " │")
            lines.append("└" + "─" * 78 + "┘")
            lines.append("")
            
            lines.append("┌" + "─" * 78 + "┐")
            lines.append("│" + "TOP 15 FILE TYPES (by size)".center(78) + "│")
            lines.append("├" + "─" * 78 + "┤")
            lines.append("│  " + "Type".ljust(15) + "Files".rjust(12) + "Storage".rjust(18) + "%".rjust(10) + "Category".rjust(18) + "  │")
            lines.append("├" + "─" * 78 + "┤")
            
            file_type_data = self._get_top_file_types()
            for data in file_type_data[:15]:
                lines.append("│  " + data['type'].ljust(15) + format_number(data['files']).rjust(12) + data['size_formatted'].rjust(18) + f"{data['percentage']:>9.1f}" + "% " + data.get('category', 'Other').rjust(18) + "  │")
            
            lines.append("└" + "─" * 78 + "┘")
            lines.append("")
            
            lines.append("┌" + "─" * 78 + "┐")
            lines.append("│" + "TOP 15 DIRECTORIES (by size)".center(78) + "│")
            lines.append("├" + "─" * 78 + "┤")
            lines.append("│  " + "Directory".ljust(40) + "Files".rjust(12) + "Storage".rjust(18) + "%".rjust(6) + "  │")
            lines.append("├" + "─" * 78 + "┤")
            
            directory_data = self._get_top_directories()
            for data in directory_data[:15]:
                lines.append("│  " + data['name'].ljust(40) + format_number(data['files']).rjust(12) + data['size_formatted'].rjust(18) + f"{data['percentage']:>5.1f}" + "%  │")
            
            lines.append("└" + "─" * 78 + "┘")
            lines.append("")
            
            lines.append("┌" + "─" * 78 + "┐")
            lines.append("│" + "CATEGORY BREAKDOWN".center(78) + "│")
            lines.append("├" + "─" * 78 + "┤")
            lines.append("│  " + "Category".ljust(25) + "Files".rjust(12) + "Storage".rjust(18) + "%".rjust(10) + "  │")
            lines.append("├" + "─" * 78 + "┤")
            
            category_data = self._get_category_data()
            for data in category_data:
                lines.append("│  " + data['name'].ljust(25) + format_number(data['files']).rjust(12) + data['size_formatted'].rjust(18) + f"{data['percentage']:>9.1f}" + "%  │")
            
            lines.append("└" + "─" * 78 + "┘")
            lines.append("")
            
            lines.append("┌" + "─" * 78 + "┐")
            lines.append("│" + "TOP 10 LARGEST FILES".center(78) + "│")
            lines.append("├" + "─" * 78 + "┤")
            lines.append("│  " + "#".ljust(4) + "Name".ljust(35) + "Size".rjust(15) + "Location".rjust(20) + "  │")
            lines.append("├" + "─" * 78 + "┤")
            
            for i, file_info in enumerate(self.largest_files[:10], 1):
                name = file_info['name'][:32] + "..." if len(file_info['name']) > 35 else file_info['name']
                loc = file_info['parent'][:17] + "..." if len(file_info['parent']) > 20 else file_info['parent']
                lines.append("│  " + str(i).ljust(4) + name.ljust(35) + file_info['size_formatted'].rjust(15) + loc.rjust(20) + "  │")
            
            lines.append("└" + "─" * 78 + "┘")
            lines.append("")
            
            if self.duplicate_files:
                lines.append("┌" + "─" * 78 + "┐")
                lines.append("│" + "DUPLICATE FILES WARNING".center(78) + "│")
                lines.append("├" + "─" * 78 + "┤")
                total_wasted = sum(f[0]['size'] * (len(f) - 1) for f in self.duplicate_files.values())
                lines.append("│  Duplicate Groups: " + str(len(self.duplicate_files)).rjust(58) + " │")
                lines.append("│  Wasted Space: " + format_size(total_wasted).rjust(58) + " │")
                lines.append("└" + "─" * 78 + "┘")
                lines.append("")
            
            lines.append("╔" + "═" * 78 + "╗")
            lines.append("║" + "END OF REPORT".center(78) + "║")
            lines.append("╚" + "═" * 78 + "╝")
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            print(f"   {Colors.GREEN}[+] Summary Text: {output_file}{Colors.ENDC}")
            
        except OSError as error:
            print(f"   {Colors.FAIL}[!] ERROR: Could not create summary text: {error}{Colors.ENDC}")
    
    def _generate_duplicate_report(self) -> None:
        """Generate detailed duplicate files report."""
        output_file = self.output_dir / "DUPLICATES.txt"
        
        try:
            lines = []
            lines.append("=" * 80)
            lines.append("DUPLICATE FILES REPORT".center(80))
            lines.append("=" * 80)
            lines.append("")
            lines.append("Root: " + str(self.root.resolve()))
            lines.append("Generated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            lines.append("")
            
            total_wasted = 0
            for hash_val, files in self.duplicate_files.items():
                wasted = files[0]['size'] * (len(files) - 1)
                total_wasted += wasted
                
                lines.append("-" * 80)
                lines.append("Hash: " + hash_val)
                lines.append("File Size: " + files[0]['size_formatted'])
                lines.append("Occurrences: " + str(len(files)))
                lines.append("Wasted Space: " + format_size(wasted))
                lines.append("")
                lines.append("Locations:")
                for i, file_info in enumerate(files, 1):
                    lines.append("  " + str(i) + ". " + file_info['path'])
                lines.append("")
            
            lines.append("=" * 80)
            lines.append("Total Wasted Space: " + format_size(total_wasted))
            lines.append("=" * 80)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            print(f"   {Colors.GREEN}[+] Duplicate Report: {output_file}{Colors.ENDC}")
            
        except OSError as error:
            print(f"   {Colors.FAIL}[!] ERROR: Could not create duplicate report: {error}{Colors.ENDC}")
    
    def _print_terminal_summary(self) -> None:
        """Print beautiful terminal summary."""
        WIDTH = 80
        
        print("\n" + Colors.BOLD + "=" * WIDTH + Colors.ENDC)
        print(Colors.HEADER + Colors.BOLD + "FOLDER STORAGE ANALYTICS PRO".center(WIDTH) + Colors.ENDC)
        print(Colors.CYAN + "Professional Analysis Complete".center(WIDTH) + Colors.ENDC)
        print(Colors.BOLD + "=" * WIDTH + Colors.ENDC)
        print("")
        print(f"{Colors.BLUE}Root:{Colors.ENDC} " + str(self.root.resolve()))
        print("")
        print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
        print(Colors.GREEN + Colors.BOLD + "SUMMARY STATISTICS".center(WIDTH) + Colors.ENDC)
        print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
        print("  " + Colors.CYAN + "Total Files:" + Colors.ENDC + "          " + format_number(self.total_files).rjust(20))
        print("  " + Colors.CYAN + "Total Directories:" + Colors.ENDC + "    " + format_number(self.total_directories).rjust(20))
        print("  " + Colors.CYAN + "Total Storage:" + Colors.ENDC + "        " + format_size(self.total_storage).rjust(20))
        print("  " + Colors.CYAN + "Unique File Types:" + Colors.ENDC + "    " + format_number(len(self.file_type_count)).rjust(20))
        print("  " + Colors.CYAN + "File Categories:" + Colors.ENDC + "      " + format_number(len(self.file_category_count)).rjust(20))
        print("")
        
        print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
        print(Colors.GREEN + Colors.BOLD + "TOP 5 FILE TYPES (by size)".center(WIDTH) + Colors.ENDC)
        print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
        
        for i, (file_type, size) in enumerate(
            sorted(self.file_type_size.items(), key=lambda x: x[1], reverse=True)[:5],
            start=1
        ):
            count = self.file_type_count[file_type]
            percentage = (size / self.total_storage * 100) if self.total_storage else 0
            icon = get_file_icon(file_type)
            print("  " + Colors.YELLOW + str(i) + "." + Colors.ENDC + " " + icon + " " + file_type.ljust(12) + " " + format_number(count).rjust(8) + " files  " + format_size(size).rjust(12) + "  (" + f"{percentage:>5.1f}" + "%)")
        
        print("")
        print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
        print(Colors.GREEN + Colors.BOLD + "TOP 5 DIRECTORIES (by size)".center(WIDTH) + Colors.ENDC)
        print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
        
        for i, (directory, size) in enumerate(
            sorted(self.directory_size.items(), key=lambda x: x[1], reverse=True)[:5],
            start=1
        ):
            count = self.directory_file_count[directory]
            percentage = (size / self.total_storage * 100) if self.total_storage else 0
            print("  " + Colors.YELLOW + str(i) + "." + Colors.ENDC + " " + directory.ljust(20) + " " + format_number(count).rjust(8) + " files  " + format_size(size).rjust(12) + "  (" + f"{percentage:>5.1f}" + "%)")
        
        print("")
        print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
        print(Colors.GREEN + Colors.BOLD + "CATEGORY BREAKDOWN".center(WIDTH) + Colors.ENDC)
        print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
        
        for i, (category, size) in enumerate(
            sorted(self.file_category_size.items(), key=lambda x: x[1], reverse=True)[:5],
            start=1
        ):
            count = self.file_category_count[category]
            percentage = (size / self.total_storage * 100) if self.total_storage else 0
            print("  " + Colors.YELLOW + str(i) + "." + Colors.ENDC + " " + category.ljust(15) + " " + format_number(count).rjust(8) + " files  " + format_size(size).rjust(12) + "  (" + f"{percentage:>5.1f}" + "%)")
        
        if self.duplicate_files:
            print("")
            print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
            print(Colors.WARNING + Colors.BOLD + "DUPLICATE FILES DETECTED".center(WIDTH) + Colors.ENDC)
            print(Colors.BOLD + "-" * WIDTH + Colors.ENDC)
            total_wasted = sum(f[0]['size'] * (len(f) - 1) for f in self.duplicate_files.values())
            print("  " + Colors.WARNING + "Groups:" + Colors.ENDC + " " + str(len(self.duplicate_files)).rjust(15))
            print("  " + Colors.WARNING + "Wasted Space:" + Colors.ENDC + " " + format_size(total_wasted).rjust(15))
        
        print("")
        print(Colors.BOLD + "=" * WIDTH + Colors.ENDC)
        print(Colors.GREEN + Colors.BOLD + "ANALYSIS COMPLETE!".center(WIDTH) + Colors.ENDC)
        safe_print(f"{Colors.CYAN}All outputs saved to: {self.output_dir}{Colors.ENDC}")
        print(Colors.BOLD + "=" * WIDTH + Colors.ENDC)
        print("")
        print(f"{Colors.BLUE}Output structure:{Colors.ENDC}")
        print("   " + str(self.output_dir) + "/")
        print("   ├── reports/")
        print("   │   └── " + self.config['html_file_name'])
        print("   ├── data/")
        print("   │   ├── " + self.config['json_file_name'])
        print("   │   └── " + self.config['csv_file_name'])
        print("   ├── " + self.config['readme_file_name'])
        print("   ├── SUMMARY.txt")
        if self.duplicate_files:
            print("   └── DUPLICATES.txt")
        print("")
    
    def _get_top_file_types(self) -> List[Dict[str, Any]]:
        """Get top file types by size."""
        data = []
        for file_type in sorted(self.file_type_size.keys(), key=lambda x: self.file_type_size[x], reverse=True)[:self.config['top_file_types']]:
            count = self.file_type_count[file_type]
            size = self.file_type_size[file_type]
            percentage = (size / self.total_storage * 100) if self.total_storage else 0
            data.append({
                'type': file_type,
                'files': count,
                'size': size,
                'size_formatted': format_size(size),
                'percentage': percentage,
                'category': get_file_category(file_type)
            })
        return data
    
    def _get_top_directories(self) -> List[Dict[str, Any]]:
        """Get top directories by size."""
        data = []
        for directory in sorted(self.directory_size.keys(), key=lambda x: self.directory_size[x], reverse=True)[:self.config['top_directories']]:
            count = self.directory_file_count[directory]
            size = self.directory_size[directory]
            percentage = (size / self.total_storage * 100) if self.total_storage else 0
            data.append({
                'name': directory,
                'files': count,
                'size': size,
                'size_formatted': format_size(size),
                'percentage': percentage
            })
        return data
    
    def _get_category_data(self) -> List[Dict[str, Any]]:
        """Get file category data."""
        data = []
        for category in sorted(self.file_category_size.keys(), key=lambda x: self.file_category_size[x], reverse=True):
            count = self.file_category_count[category]
            size = self.file_category_size[category]
            percentage = (size / self.total_storage * 100) if self.total_storage else 0
            data.append({
                'name': category,
                'files': count,
                'size': size,
                'size_formatted': format_size(size),
                'percentage': percentage
            })
        return data
    
    def _get_age_data(self) -> List[Dict[str, Any]]:
        """Get file age distribution data."""
        age_order = ['Last 7 days', 'Last 30 days', 'Last 3 months', 'Last 6 months', 'Last year', 'Over 1 year']
        data = []
        for category in age_order:
            if category in self.age_distribution:
                size = self.age_distribution[category]
                percentage = (size / self.total_storage * 100) if self.total_storage else 0
                data.append({
                    'category': category,
                    'size': size,
                    'size_formatted': format_size(size),
                    'percentage': percentage
                })
        return data
    
    def _get_size_distribution_data(self) -> List[Dict[str, Any]]:
        """Get file size distribution data."""
        size_order = ['< 1 KB', '1 KB - 1 MB', '1 MB - 10 MB', '10 MB - 100 MB', '100 MB - 1 GB', '> 1 GB']
        data = []
        total_count = sum(self.size_distribution.values())
        for range_name in size_order:
            if range_name in self.size_distribution:
                count = self.size_distribution[range_name]
                percentage = (count / total_count * 100) if total_count else 0
                data.append({
                    'range': range_name,
                    'count': count,
                    'percentage': percentage
                })
        return data

# ============================================================
# CLI INTERFACE
# ============================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description='Folder Storage Analytics Pro - Professional folder analysis tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r"""
Examples:
  %(prog)s --path "C:\Users\User\Documents"
  %(prog)s --path "./my-folder" --theme dark --detect-duplicates
  %(prog)s --path "./data" --top-files 50 --top-dirs 20
  %(prog)s --config config.ini
        """
    )
    
    parser.add_argument('--path', '-p', type=str, help='Folder path to analyze')
    parser.add_argument('--config', '-c', type=str, help='Path to configuration file')
    parser.add_argument('--theme', '-t', choices=['modern', 'dark', 'ocean', 'sunset'], 
                       default='modern', help='Dashboard theme (default: modern)')
    parser.add_argument('--palette', choices=['gradient', 'vibrant', 'pastel', 'neon'],
                       default='gradient', help='Color palette (default: gradient)')
    parser.add_argument('--top-files', type=int, default=30, help='Number of top file types to show')
    parser.add_argument('--top-dirs', type=int, default=30, help='Number of top directories to show')
    parser.add_argument('--detect-duplicates', action='store_true', help='Enable duplicate file detection')
    parser.add_argument('--no-duplicates', action='store_true', help='Disable duplicate file detection')
    parser.add_argument('--include-hidden', action='store_true', help='Include hidden files')
    parser.add_argument('--output-dir', type=str, default='folder_analysis', help='Output directory name')
    parser.add_argument('--no-html', action='store_true', help='Disable HTML output')
    parser.add_argument('--no-json', action='store_true', help='Disable JSON output')
    parser.add_argument('--no-csv', action='store_true', help='Disable CSV output')
    parser.add_argument('--no-md', action='store_true', help='Disable Markdown output')
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 2.0.0')
    
    return parser

def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from INI file."""
    config = configparser.ConfigParser()
    config.read(config_path)
    
    settings = {}
    if 'Settings' in config:
        section = config['Settings']
        settings['folder_path'] = section.get('folder_path', DEFAULT_CONFIG['folder_path'])
        settings['top_directories'] = section.getint('top_directories', DEFAULT_CONFIG['top_directories'])
        settings['top_file_types'] = section.getint('top_file_types', DEFAULT_CONFIG['top_file_types'])
        settings['output_dir_name'] = section.get('output_dir_name', DEFAULT_CONFIG['output_dir_name'])
        settings['detect_duplicates'] = section.getboolean('detect_duplicates', DEFAULT_CONFIG['detect_duplicates'])
        settings['chart_theme'] = section.get('chart_theme', DEFAULT_CONFIG['chart_theme'])
        settings['color_scheme'] = section.get('color_scheme', DEFAULT_CONFIG['color_scheme'])
        settings['include_hidden_files'] = section.getboolean('include_hidden_files', DEFAULT_CONFIG['include_hidden_files'])
    
    return settings

def merge_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Merge default config with file config and CLI args."""
    config = DEFAULT_CONFIG.copy()
    
    # Load from file if specified
    if args.config:
        file_config = load_config_file(args.config)
        config.update(file_config)
    
    # Override with CLI args
    if args.path:
        config['folder_path'] = args.path
    config['chart_theme'] = args.theme
    config['color_scheme'] = args.palette
    config['top_file_types'] = args.top_files
    config['top_directories'] = args.top_dirs
    config['output_dir_name'] = args.output_dir
    
    if args.detect_duplicates:
        config['detect_duplicates'] = True
    if args.no_duplicates:
        config['detect_duplicates'] = False
    if args.include_hidden:
        config['include_hidden_files'] = True
    if args.no_html:
        config['html_output'] = False
    if args.no_json:
        config['json_output'] = False
    if args.no_csv:
        config['csv_output'] = False
    if args.no_md:
        config['readme_output'] = False
    
    return config

def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Merge configurations
    config = merge_config(args)
    
    # Validate path
    if not config.get('folder_path'):
        print(f"{Colors.FAIL}ERROR: No folder path specified. Use --path or set FOLDER_PATH in config.{Colors.ENDC}")
        parser.print_help()
        sys.exit(1)
    
    # Run analysis
    analyzer = FolderAnalyzer(config)
    success = analyzer.analyze()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()