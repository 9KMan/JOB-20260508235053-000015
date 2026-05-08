# Python Data Processing Automation Framework

Production-ready Python framework for processing CSV, JSON, and TXT data with validation, transformation, and multiple output formats. Designed for reliability and maintainability over speed.

**Stack:** Python 3.10+ · csv/json/stdlib only · click for CLI · jsonschema for validation

---

## Architecture

```
Input Files (CSV / JSON / TXT)
        │
        ▼
┌───────────────────┐
│   File Loader     │  Auto-detect format, stream large files (chunked, no OOM)
│  (file_loader.py) │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│     Validator     │  JSONSchema-style config, per-field errors, halt|skip modes
│  (validator.py)   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│    Transformer    │  Chainable transforms (strip→lowercase→parse_date→validate)
│ (transformer.py)  │  Parallel processing via multiprocessing.Pool
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Output Writer   │  CSV / JSON / SQLite / REST API POST (retry + backoff)
│ (output_writer.py)│
└───────────────────┘
         │
         ▼
   Error Log + Summary Report (actionable per-field errors)
```

---

## Data Sources

| Format | Detection | Streaming | Notes |
|--------|-----------|-----------|-------|
| CSV | extension + content sniff | ✓ (chunked) | Any delimiter, UTF-8, auto-header |
| JSON | extension + `[` or `{` | ✓ (NDJSON) | Array or newline-delimited |
| TXT | extension + line structure | ✓ (line-by-line) | Log files, fixed-width, custom parsing |

---

## Data Model

**Config schema (JSON):**
```json
{
  "input": { "path": "string", "format": "csv|json|txt|auto" },
  "output": { "path": "string", "format": "csv|json|sqlite|api" },
  "schema": {
    "fields": [
      { "name": "email", "type": "email", "required": true },
      { "name": "amount", "type": "float", "required": false }
    ]
  },
  "transforms": ["strip_whitespace", "lowercase_email"],
  "error_mode": "skip",
  "logging": { "level": "INFO", "path": "error.log" }
}
```

**Transform registry** — built-in transforms:
- `strip_whitespace` — remove leading/trailing whitespace
- `lowercase` — lowercase all string fields
- `uppercase` — uppercase all string fields
- `title_case` — title case string fields
- `parse_date` — parse ISO date strings
- `validate_email` — regex email validation
- `normalize_phone` — normalize to +61 format
- `lookup_enrich` — enrich with external lookup (configurable)

**Processing summary:**
```json
{
  "processed": 1000,
  "succeeded": 987,
  "failed": 13,
  "duration_seconds": 4.2,
  "errors": [{ "row": 45, "field": "email", "reason": "invalid format", "value": "not-an-email" }]
}
```

---

## CLI Reference

```bash
# Run full pipeline
python main.py run --input data.csv --config config.json --output results.csv

# Validate without transform
python main.py validate --input data.csv --schema schema.json

# Batch process all files in directory
python main.py batch --input-dir ./data --config config.json

# Generate error summary from log
python main.py report --log error.log

# Dry run (validate only, no output)
python main.py run --input data.csv --config config.json --dry-run
```

**Flags:**
| Flag | Description | Default |
|------|-------------|---------|
| `--input`, `-i` | Input file path | required |
| `--output`, `-o` | Output file path | stdout |
| `--config`, `-c` | Config JSON file | config.json |
| `--log-level` | DEBUG/INFO/WARNING/ERROR | INFO |
| `--dry-run` | Validate only | False |
| `--parallel` | Enable multiprocessing | False |

---

## Installation

```bash
# No external dependencies beyond stdlib + click + jsonschema
pip install -r requirements.txt

# requirements.txt contents:
# click>=8.0
# jsonschema>=4.0
```

No system dependencies required — pure Python, cross-platform.

---

## Quality Guarantees

- **Zero hard crash:** All errors logged with field+row+reason, pipeline continues or fails gracefully
- **Idempotent:** Same input produces same output (deterministic transforms)
- **Large file support:** Stream processing for 100k+ row CSV without OOM (configurable chunk size)
- **UTF-8 safe:** Handles international characters in all fields
- **Schema validation before transform:** Bad input → clear error message, not corrupted output
- **Actionable errors:** Per-field, per-row error messages with actual bad value captured

---

## Output Format

**CSV output (UTF-8, Excel-safe):**
```csv
name,email,phone,amount,status,error
"Acme Corp","contact@acme.com","+61 4 1234 5678",1500.00,processed,
"Beta Ltd","not-valid","+61 4 0000 0000",0.00,failed,"[45] email: invalid format"
```

**JSON output:**
```json
{
  "summary": { "processed": 1000, "succeeded": 987, "failed": 13 },
  "results": [
    { "name": "Acme Corp", "email": "contact@acme.com", "status": "processed" },
    { "name": "Beta Ltd", "email": "not-valid", "status": "failed", "error": "invalid email" }
  ]
}
```

---

## Project Structure

```
JOB-20260508235053-000015/
├── README.md
├── main.py                          # CLI entry point (click)
├── requirements.txt
├── SPEC.md
├── processors/
│   ├── __init__.py
│   ├── file_loader.py               # CSV/JSON/TXT auto-detect + streaming
│   ├── validator.py                 # JSONSchema-style validation
│   ├── transformer.py               # Chainable transforms + parallel
│   └── output_writer.py             # CSV/JSON/SQLite/API output
├── utils/
│   ├── __init__.py
│   └── error_handler.py             # Structured logging + error summary
└── tests/
    ├── __init__.py
    ├── test_file_loader.py
    ├── test_validator.py
    └── test_transformer.py
```

---

## Limitations

- **GUI / web interface:** Not included in V1 — CLI only
- **Database connections:** MySQL/PostgreSQL not supported — use SQLite for persistence
- **Real-time streaming:** Kafka/RabbitMQ not supported — batch file processing only
- **ML/AI inference:** Not included — pure data processing
- **Scheduled jobs:** Cron/scheduler not included — manual trigger only
- **Large JSON arrays:** Full JSON array loaded in memory — use NDJSON for streaming