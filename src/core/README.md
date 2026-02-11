# src/core/ -- Shared Infrastructure

Configuration, persistence, and logging used across all other packages.

## Modules

| Module | Purpose |
|---|---|
| `config.py` | YAML config loading and validation with typed dataclasses (`BotConfig`, `TelegramConfig`, `ClaudeConfig`, `SessionsConfig`, `DatabaseConfig`, `DebugConfig`) |
| `database.py` | Async SQLite wrapper (`Database` class) for persisting session records -- create, update status, query history, mark lost sessions on startup |
| `log_setup.py` | Custom `TRACE` log level (5), console and file handler setup, optional trace-file output to `debug/` directory |

## Key Patterns

- **YAML config with typed dataclasses:** `load_config()` reads a YAML file and returns a `BotConfig` dataclass tree. Each section maps to a nested dataclass with defaults. Validation happens at load time.
- **Custom TRACE log level (5):** Below DEBUG (10). Used for high-volume diagnostic output (every poll cycle, every screen classification). Enabled with `--trace` flag; optionally mirrored to terminal with `--verbose`.
- **Async SQLite:** All database operations are `async` via `aiosqlite`. The `Database` class manages connection lifecycle (`initialize()` / `close()`) and provides typed query methods.
