# Changelog

## v1.0.0 - Initial Release

### Core
- SQLite database with WAL mode and dedicated writer thread
- Batch insert/update operations (100 items per batch)
- Comprehensive indexing strategy (15+ indexes)
- Protocol capabilities table for deduplication

### Engine
- Fair round-robin scheduler with per-protocol target management
- Independent protocol validation (HTTP, HTTPS, SOCKS4, SOCKS5)
- Connection pooling and session reuse
- Automatic endpoint failover with health tracking
- Retry strategy with configurable delays

### GUI
- 8-page navigation: Dashboard, Collect, Proxies, Sources, Export, History, Logs, Settings
- Dark/Light theme support via CustomTkinter
- Real-time statistics and activity logging
- Responsive resizable layout
- Sidebar navigation with 220px width

### Sources
- 16 built-in curated public sources
- Custom source management with add/edit/delete
- Source health tracking and individual testing
- Priority-based fetching

### Export
- TXT, CSV, JSON formats
- With/without scheme options
- Grouped/separate/both grouping modes
- Per-protocol file separation

### Quality System
- Evidence-based anonymity detection (Elite/Anonymous/Transparent)
- Quality score 0-100 based on latency, reliability, freshness, protocols, history
- Latency and reliability tracking per proxy
- Success rate calculation

### Diagnostics
- Internet connectivity check
- DNS resolution test
- SQLite WAL verification
- SOCKS library detection
- Export folder writability
- HTTP/HTTPS endpoint reachability
- GeoIP service check
- Python dependency verification

### Security
- No cloud services required
- No browser automation
- No third-party validation APIs
- All operations run locally
