# Proxy Collector Pro

Enterprise-grade Windows desktop application for proxy collection, validation, and management.

## Features

- **16 Built-in Curated Sources** - Ready to use proxy sources from GitHub and public APIs
- **Multi-Protocol Support** - HTTP, HTTPS, SOCKS4, SOCKS5 with independent validation
- **Fair Round-Robin Scheduler** - Prevents protocol starvation, respects per-protocol targets
- **Quality Scoring** - 0-100 score based on latency, reliability, freshness, protocol diversity
- **GeoIP Resolution** - Optional country/city/ISP/ASN detection (failure ignored)
- **Anonymity Detection** - Elite, Anonymous, Transparent classification (evidence-based)
- **Export Engine** - TXT, CSV, JSON with scheme/grouping options
- **SQLite WAL Mode** - High-performance concurrent database with dedicated writer thread
- **Dark/Light Themes** - Modern CustomTkinter UI with sidebar navigation
- **Diagnostics** - Built-in system health checks

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13 |
| GUI | CustomTkinter |
| Database | SQLite (WAL Mode) |
| HTTP | requests |
| SOCKS | PySocks |
| Concurrency | ThreadPoolExecutor |
| Packaging | PyInstaller |

## Project Structure

```
proxy_collector_pro/
├── config/              # Constants and settings
│   ├── constants.py
│   └── settings.py
├── core/                # Database, models, events
│   ├── database.py
│   ├── models.py
│   └── events.py
├── engine/              # Validation and collection
│   ├── endpoints.py
│   ├── geoip.py
│   ├── anonymity.py
│   ├── validator.py
│   ├── scheduler.py
│   └── collector.py
├── sources/             # Source management
│   ├── built_in.py
│   └── manager.py
├── gui/                 # User interface
│   ├── components.py
│   ├── app.py
│   └── pages/
│       ├── dashboard.py
│       ├── collect.py
│       ├── proxies.py
│       ├── sources.py
│       ├── export.py
│       ├── history.py
│       ├── logs.py
│       └── settings.py
├── utils/               # Utilities
│   ├── logger.py
│   ├── helpers.py
│   ├── diagnostics.py
│   └── exporter.py
├── tests/               # Test suite
│   ├── test_database.py
│   ├── test_scheduler.py
│   └── test_export.py
├── main.py              # Entry point
├── requirements.txt     # Dependencies
├── build_exe.bat        # Windows build script
├── proxy_collector.spec # PyInstaller spec
├── README.md            # This file
└── CHANGELOG.md         # Version history
```

## Quick Start

### Prerequisites

- Windows 10/11
- Python 3.13 (64-bit)
- Internet connection

### Installation

1. **Extract the archive** to a folder, e.g. `C:\ProxyCollectorPro`

2. **Open Command Prompt** in the project folder:
   ```cmd
   cd C:\ProxyCollectorPro
   ```

3. **Create virtual environment** (recommended):
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

5. **Run the application**:
   ```cmd
   python main.py
   ```

### Build Portable EXE

Double-click `build_exe.bat` or run:
```cmd
build_exe.bat
```

The executable will be created in `dist\ProxyCollectorPro.exe`.

To build manually with PyInstaller:
```cmd
pyinstaller proxy_collector.spec
```

## Usage Guide

### Dashboard
View real-time statistics: total proxies, alive count, protocol distribution, and recent activity log.

### Collect
1. Select a preset (Fast/Balanced/Quality/Deep)
2. Set per-protocol targets
3. Click **Start** to fetch from sources and validate
4. Use **Pause/Resume** or **Stop** to control

### Proxies
Browse, search, and filter the proxy database. Filter by protocol, status, anonymity, country. Delete individual proxies or clear all dead ones.

### Sources
Manage proxy sources. 16 built-in sources are pre-configured. Add custom sources with URL, protocol, and priority. Test sources individually.

### Export
Export validated proxies in TXT, CSV, or JSON format. Options:
- **With/Without scheme**: `http://1.2.3.4:8080` vs `1.2.3.4:8080`
- **Grouping**: Grouped by protocol, separate files, or both

### History
View validation history per proxy. Check success rates, latency trends, and endpoint details.

### Logs
Persistent application logs with filtering by level (DEBUG, INFO, SUCCESS, WARNING, ERROR). Export logs to file.

### Settings
- **General**: Theme (dark/light)
- **Collection**: Threads, timeout, retries
- **Targets**: Default per-protocol targets
- **GeoIP**: Enable/disable resolution
- **Export**: Default format
- **Logging**: Log level
- **Diagnostics**: Run system health checks

## Architecture Highlights

### Database
- SQLite with WAL (Write-Ahead Logging) mode
- Dedicated writer thread with batch operations
- 15+ indexes for fast queries
- Protocol capabilities table for deduplication

### Validation Engine
- Independent queues per protocol
- Fair round-robin scheduler
- Connection pooling and session reuse
- Automatic endpoint failover
- Retry strategy with exponential backoff

### Thread Safety
- UI updates only from main thread
- Workers communicate via queues
- Immutable snapshots for UI
- No shared mutable iteration

## Testing

Run the test suite:
```cmd
python -m unittest discover -s tests -v
```

Tests cover:
- Database operations (insert, query, stats)
- Scheduler deduplication and target management
- Export engine (TXT, CSV, JSON)

## License

Proprietary - Elite Software Engineering Team
