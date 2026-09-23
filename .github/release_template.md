<p align="center">
  <img src="https://raw.githubusercontent.com/rigitty/VortexDBA/main/logo.png" alt="VortexDBA Logo" width="140" height="140" />
</p>

# VortexDBA Release

Autonomous SQL Server Performance Tuning and Index Optimization Engine

---

## Overview

VortexDBA is an autonomous, intelligent index tuning and query optimization engine designed specifically for Microsoft SQL Server workloads. It monitors database queries with zero profiler overhead, generates non-clustered index recommendations, performs controlled before-and-after benchmarks, and automatically rolls back changes if latency degrades.

---

## Key Features

- **Real-Time Workload Capture:** Discovers high-impact queries and execution bottlenecks via SQL Server Dynamic Management Views (DMVs) without profiling overhead.
- **Non-Clustered Index Advisor:** Analyzes query predicates, join columns, equality/range conditions, and sorting requirements to recommend optimal index definitions.
- **Controlled Benchmarking and Automatic Rollback:** Executes pre- and post-optimization latency tests. If performance drops below the defined threshold, structural changes are rolled back automatically.
- **Unused Index Inventory:** Tracks cumulative seek/scan counters to detect dormant indexes that consume disk space and degrade write operations.
- **Safety Guardrails:** Configurable limits for maximum indexes per table, global quotas, operation cooldown intervals, and dry-run defaults.
- **Native Desktop GUI:** Built with PyQt6, featuring modern dark and light themes along with multi-language support (English and Turkish).

---

## Download and Installation (Windows)

No Python installation or external dependencies are required.

1. Download the Windows portable package (`VortexDBA-*-windows-x64.zip`) from the **Assets** section below.
2. Extract the archive to your preferred directory.
3. Open `config.yaml` with any text editor and specify your SQL Server connection details:

```yaml
database:
  host: "localhost"
  port: 1433
  database: "YourDatabaseName"
  user: "sa"
  password: "YourStrongPassword"
```

4. Launch the application by running `VortexDBA.exe`.

---

## Running from Source or Docker

### Run from Source

```bash
git clone https://github.com/rigitty/VortexDBA.git
cd VortexDBA
pip install -r requirements.txt
python app.py
```

### Run with Docker Compose

```bash
docker-compose up -d
```
