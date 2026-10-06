"""Shared foundation for every BINMAN pipeline stage.

Three jobs:

1. **Config.** Load `config/tuning.toml` and `config/thresholds.toml`. Nothing in
   this project reads a core count or a scientific cutoff from anywhere else.
2. **Manifests.** Every stage appends one JSON line per item to
   `data/manifests/<stage>.jsonl`. On restart a stage reads its own manifest and
   skips what is already done, so the process can be killed at any moment
   (spec Section 0 rule 4).
3. **Polite IO.** A cached, rate-limited, retried HTTP client. Every response is
   cached under `data/cache/<source>/` keyed by a request hash and is never
   re-fetched unless `refresh=True` (spec 4.1).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA = ROOT / "data"
CACHE = DATA / "cache"
MANIFESTS = DATA / "manifests"
VALIDATION = DATA / "validation"
REFERENCE = DATA / "reference"
INTERIM = DATA / "interim"
ATLAS = DATA / "atlas"
BUILD_LOG = ROOT / "BUILD_LOG.md"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #

class ConfigError(RuntimeError):
    """Raised when a config file or a required key is missing.

    Deliberately fatal: a stage that silently falls back to a hard-coded
    threshold would violate the spec's central rule and nobody would notice.
    """


@dataclass(frozen=True)
class Config:
    tuning: dict
    thresholds: dict
    hardware: dict

    def t(self, path: str) -> Any:
        """Fetch a threshold by dotted path, e.g. `bridging.contact_cutoff_a`."""
        return _dotted(self.thresholds, path, "config/thresholds.toml")

    def u(self, path: str) -> Any:
        """Fetch a tuning value by dotted path, e.g. `compute.cpu_workers`."""
        return _dotted(self.tuning, path, "config/tuning.toml")

    def h(self, path: str) -> Any:
        return _dotted(self.hardware, path, "config/hardware.toml")


def _dotted(blob: dict, path: str, origin: str) -> Any:
    node: Any = blob
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f"{origin} has no key '{path}'")
        node = node[part]
    return node


def _read_toml(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(
            f"{path.relative_to(ROOT)} is missing. Run `pixi run hwprobe` first."
        )
    with path.open("rb") as handle:
        return tomllib.load(handle)


_CONFIG: Config | None = None


def load_config(refresh: bool = False) -> Config:
    """Load and memoise the three config files."""
    global _CONFIG
    if _CONFIG is None or refresh:
        _CONFIG = Config(
            tuning=_read_toml(CONFIG_DIR / "tuning.toml"),
            thresholds=_read_toml(CONFIG_DIR / "thresholds.toml"),
            hardware=_read_toml(CONFIG_DIR / "hardware.toml"),
        )
    return _CONFIG


def apply_env(config: Config | None = None) -> None:
    """Export the PyTorch and OpenMP settings from tuning.toml (spec 2.2)."""
    config = config or load_config()
    for key, value in config.u("env").items():
        os.environ.setdefault(key, str(value))


# --------------------------------------------------------------------------- #
# logging
# --------------------------------------------------------------------------- #

_LOG_LOCK = threading.Lock()


def log_event(phase: str, message: str, echo: bool = True) -> None:
    """Append one timestamped row to BUILD_LOG.md.

    The log is a markdown table, so the row format is fixed. Pipe characters in
    the message are escaped rather than breaking the table.
    """
    safe = message.replace("|", "\\|").strip()
    row = f"| {utcnow()} | {phase} | {safe} |\n"
    with _LOG_LOCK:
        with BUILD_LOG.open("a", encoding="utf-8") as handle:
            handle.write(row)
    if echo:
        print(f"[{phase}] {safe}", flush=True)


# --------------------------------------------------------------------------- #
# manifests
# --------------------------------------------------------------------------- #

@dataclass
class Manifest:
    """An append-only JSONL record of one stage's work.

    `key` identifies an item (a PDB id, a UniProt accession, a dataset name).
    `done()` is the resumability primitive: a stage asks it what to skip. A row
    whose status starts with "failed:" counts as attempted and is not retried,
    because the fallback ladder has already run on it; `retry_failed=True`
    overrides that for a deliberate re-run.
    """

    stage: str
    path: Path = field(init=False)
    _seen: dict[str, str] = field(init=False, default_factory=dict)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)

    def __post_init__(self) -> None:
        MANIFESTS.mkdir(parents=True, exist_ok=True)
        self.path = MANIFESTS / f"{self.stage}.jsonl"
        self._seen = {}
        if self.path.exists():
            for row in self.read():
                key = row.get("key")
                if key is not None:
                    self._seen[str(key)] = str(row.get("status", "unknown"))

    def read(self) -> Iterator[dict]:
        """Yield every row, skipping any truncated final line from a kill."""
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # A process killed mid-write leaves a partial line. One
                    # partial row is expected and is not an error.
                    continue

    def done(self, key: str, retry_failed: bool = False) -> bool:
        status = self._seen.get(str(key))
        if status is None:
            return False
        if retry_failed and status.startswith("failed:"):
            return False
        return True

    def record(self, key: str, status: str = "ok", **fields: Any) -> dict:
        """Append one row. Flushed and fsynced so a kill cannot lose it."""
        row = {"key": str(key), "status": status, "at": utcnow(), **fields}
        line = json.dumps(row, separators=(",", ":"), default=str) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            self._seen[row["key"]] = status
        return row

    def fail(self, key: str, reason: str, **fields: Any) -> dict:
        """Record a failure as data, not as an exception (spec Section 0 rule 3)."""
        return self.record(key, status=f"failed:{reason}", **fields)

    def counts(self) -> dict[str, int]:
        """Status tallies, with every failure reason collapsed to `failed`."""
        tally: dict[str, int] = {}
        for status in self._seen.values():
            label = "failed" if status.startswith("failed:") else status
            tally[label] = tally.get(label, 0) + 1
        tally["total"] = len(self._seen)
        return tally

    def failures(self) -> list[dict]:
        return [r for r in self.read() if str(r.get("status", "")).startswith("failed:")]


# --------------------------------------------------------------------------- #
# polite, cached IO
# --------------------------------------------------------------------------- #

# The sentinel for "an empty body is still an error here", which is the default.
# A plain None would make `no_content=None` indistinguishable from not passing it,
# and None is the natural thing a caller wants an empty body to mean.
_RAISE_ON_EMPTY = object()


class RateLimiter:
    """A simple thread-safe minimum-interval gate."""

    def __init__(self, per_second: float) -> None:
        self._interval = 1.0 / per_second if per_second > 0 else 0.0
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        if self._interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                time.sleep(self._next - now)
                now = time.monotonic()
            self._next = now + self._interval


GZIP_MAGIC = b"\x1f\x8b"


def _maybe_gunzip(content: bytes) -> bytes:
    """Decompress a gzip body that arrived without a Content-Encoding header.

    UniProt's stream endpoint serves gzip but does not always declare it, so
    httpx hands back the raw deflate stream. Sniffing the magic bytes is the
    only reliable test.
    """
    if content[:2] != GZIP_MAGIC:
        return content
    import gzip

    try:
        return gzip.decompress(content)
    except OSError:
        return content


def request_hash(method: str, url: str, params: Any = None, body: Any = None) -> str:
    """Stable cache key for a request."""
    payload = json.dumps(
        {"m": method.upper(), "u": url, "p": params, "b": body},
        sort_keys=True, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


class Fetcher:
    """Cached, rate-limited, retried HTTP access to one named source.

    Every response lands in `data/cache/<source>/<hash>.{json,bin}` and is
    returned from there on every later call. `refresh=True` is the only way to
    re-fetch, which keeps a long build reproducible and keeps the public APIs
    unbothered on restart.
    """

    USER_AGENT = (
        "BINMAN/0.1 (academic structural bioinformatics; "
        "https://github.com/bellcheddar/BINMAN; marc@marcdeller.com)"
    )

    def __init__(
        self,
        source: str,
        config: Config | None = None,
        rate_per_second: float | None = None,
        refresh: bool = False,
    ) -> None:
        self.source = source
        self.config = config or load_config()
        self.refresh = refresh
        self.dir = CACHE / source
        self.dir.mkdir(parents=True, exist_ok=True)
        if rate_per_second is None:
            key = f"io.{source}_rate_limit_per_sec"
            try:
                rate_per_second = float(self.config.u(key))
            except ConfigError:
                rate_per_second = float(self.config.u("io.generic_rate_limit_per_sec"))
        self.limiter = RateLimiter(rate_per_second)
        self.attempts = int(self.config.u("io.retry_attempts"))
        self.backoff = float(self.config.u("io.retry_backoff_seconds"))
        self.timeout = float(self.config.u("io.http_timeout_seconds"))
        self.hits = 0
        self.misses = 0

    # -- cache paths -------------------------------------------------------- #

    def _paths(self, key: str, binary: bool) -> tuple[Path, Path]:
        suffix = ".bin" if binary else ".json"
        return self.dir / f"{key}{suffix}", self.dir / f"{key}.meta.json"

    def cached(self, key: str, binary: bool = False) -> bool:
        return self._paths(key, binary)[0].exists()

    # -- the one network primitive ------------------------------------------ #

    def _attempt(self, method: str, url: str, params, json_body, headers) -> tuple[bytes, dict]:
        import httpx  # imported late so `--help` works without the compute env

        merged = {"User-Agent": self.USER_AGENT, "Accept-Encoding": "gzip"}
        merged.update(headers or {})
        last: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            self.limiter.wait()
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    response = client.request(
                        method, url, params=params, json=json_body, headers=merged
                    )
                # 404 is an answer, not a failure: the record does not exist.
                if response.status_code == 404:
                    raise FileNotFoundError(f"404 {url}")
                # 429 and 5xx are worth retrying; everything else is not.
                if response.status_code == 429 or response.status_code >= 500:
                    raise RuntimeError(f"HTTP {response.status_code} {url}")
                response.raise_for_status()
                meta = {
                    "source": self.source,
                    "url": str(response.url),
                    "method": method.upper(),
                    "status_code": response.status_code,
                    "retrieved_at": utcnow(),
                    "content_type": response.headers.get("content-type", ""),
                    "bytes": len(response.content),
                    "attempts": attempt,
                }
                return response.content, meta
            except FileNotFoundError:
                raise
            except Exception as exc:  # noqa: BLE001 - every transport error retries alike
                last = exc
                if attempt < self.attempts:
                    time.sleep(self.backoff * (2 ** (attempt - 1)))
        raise RuntimeError(f"{self.source}: {self.attempts} attempts failed for {url}: {last}")

    def fetch_bytes(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Any = None,
        json_body: Any = None,
        headers: dict | None = None,
        key: str | None = None,
    ) -> bytes:
        key = key or request_hash(method, url, params, json_body)
        blob_path, meta_path = self._paths(key, binary=True)
        if blob_path.exists() and not self.refresh:
            self.hits += 1
            return blob_path.read_bytes()
        content, meta = self._attempt(method, url, params, json_body, headers)
        blob_path.write_bytes(content)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        self.misses += 1
        return content

    def fetch_json(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Any = None,
        json_body: Any = None,
        headers: dict | None = None,
        key: str | None = None,
        no_content: Any = _RAISE_ON_EMPTY,
    ) -> Any:
        """Fetch and parse JSON, caching the parsed body.

        `no_content` is what an empty 2xx body means to this caller. The RCSB
        Search API answers a zero-hit query with 204 and no body at all, so
        "nothing matched" and "the transfer was truncated" look identical on the
        wire, and a stage that guessed would under-count in silence. A caller
        that knows an empty body is a legitimate answer says so and gets that
        value; every other caller still gets the exception.
        """
        key = key or request_hash(method, url, params, json_body)
        blob_path, meta_path = self._paths(key, binary=False)
        if blob_path.exists() and not self.refresh:
            self.hits += 1
            try:
                return json.loads(blob_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # A corrupt cache entry is a cache miss, not a build failure.
                blob_path.unlink(missing_ok=True)
        content, meta = self._attempt(method, url, params, json_body, headers)
        content = _maybe_gunzip(content)
        text = content.decode("utf-8", errors="replace")
        if not text.strip() and no_content is not _RAISE_ON_EMPTY:
            parsed = no_content
        else:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"{self.source}: {url} returned non-JSON: {text[:200]}") from exc
        blob_path.write_text(json.dumps(parsed, separators=(",", ":")))
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        self.misses += 1
        return parsed

    def provenance(self, key: str, binary: bool = False) -> dict:
        """The recorded metadata for a cached response, for the provenance table."""
        meta_path = self._paths(key, binary)[1]
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return {}


# --------------------------------------------------------------------------- #
# small helpers used across stages
# --------------------------------------------------------------------------- #

def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":"), default=str) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def free_disk_gb(path: Path = ROOT) -> float:
    import shutil
    return round(shutil.disk_usage(path).free / (1024 ** 3), 1)


def check_gate_g5(config: Config | None = None) -> bool:
    """True when free space is still above the G5 floor."""
    config = config or load_config()
    floor = float(config.u("disk.gate_g5_free_gb_floor"))
    free = free_disk_gb()
    if free < floor:
        log_event("gate", f"G5 candidate: {free} GB free, floor is {floor} GB")
        return False
    return True


def open_gate(gate: str, what_is_needed: str, done: str, next_step: str,
              unblock_command: str = "") -> None:
    """Write GATE_OPEN.md and notify, then let the caller carry on (spec Section 0)."""
    body = [
        f"# Gate {gate} open",
        "",
        f"Opened at {utcnow()}.",
        "",
        "## What is needed",
        "",
        what_is_needed.strip(),
        "",
    ]
    if unblock_command:
        body += ["## What unblocks it", "", "```bash", unblock_command.strip(), "```", ""]
    body += ["## Already done", "", done.strip(), "",
             "## What happens next", "", next_step.strip(), ""]
    (ROOT / "GATE_OPEN.md").write_text("\n".join(body))
    log_event("gate", f"{gate} opened: {what_is_needed.splitlines()[0][:120]}")
    try:
        import subprocess
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{what_is_needed.splitlines()[0][:120]}" '
             f'with title "BINMAN gate {gate}" sound name "Glass"'],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass
