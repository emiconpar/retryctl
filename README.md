# retryctl

A CLI tool for wrapping shell commands with configurable retry logic and backoff strategies.

---

## Installation

```bash
pip install retryctl
```

Or install from source:

```bash
git clone https://github.com/yourname/retryctl.git && cd retryctl && pip install .
```

---

## Usage

```bash
retryctl [OPTIONS] -- <command>
```

**Examples:**

```bash
# Retry a command up to 5 times with exponential backoff
retryctl --retries 5 --backoff exponential -- curl https://example.com/api

# Retry with a fixed 2-second delay between attempts
retryctl --retries 3 --delay 2 -- ./deploy.sh

# Stop retrying if the command exits with code 0 or 2
retryctl --retries 4 --stop-on 0,2 -- python sync.py
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--retries` | `3` | Number of retry attempts |
| `--delay` | `1` | Initial delay in seconds between retries |
| `--backoff` | `fixed` | Backoff strategy: `fixed`, `exponential`, or `linear` |
| `--stop-on` | `0` | Comma-separated exit codes that halt retrying |
| `--timeout` | None | Per-attempt timeout in seconds |

---

## Backoff Strategies

- **fixed** — waits the same `--delay` between every attempt
- **linear** — increases delay by `--delay` each attempt (2s, 4s, 6s, ...)
- **exponential** — doubles the delay each attempt (1s, 2s, 4s, 8s, ...)

---

## License

MIT © 2024 [yourname](https://github.com/yourname)