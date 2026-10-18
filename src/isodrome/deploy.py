"""Deploying transformers: pack a project, upload it, build and verify it, then (for a stateful
transformer) wait for its backfill. Shared by the SDK (`client.deploy_transformer`) and the CLI
(`iso transformer deploy/test`)."""

from __future__ import annotations

import io
import json
import os
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from isodrome import errors
from isodrome.parse import format_ns, parse_duration, to_duration_ns
from isodrome.v1 import isodrome_pb2 as pb

# Never packed into a project.
IGNORED = {".git", ".hg", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache",
           ".ruff_cache", ".DS_Store", ".env", ".idea", "dist", "build", ".ipynb_checkpoints"}
MAX_BUNDLE_BYTES = 50 * 1024 * 1024
CHUNK_BYTES = 1 << 20
FINISHED = ("ready", "build_failed", "verification_failed", "cancelled")
BASES = {"received": pb.AS_OF_BASIS_RECEIVED, "published": pb.AS_OF_BASIS_PUBLISHED}


def pack(directory: str | Path) -> bytes:
    """A project directory as a zip (sorted, so the same files give the same bundle)."""
    root = Path(directory)
    out = io.BytesIO()
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in IGNORED)
            for name in sorted(filenames):
                if name in IGNORED or name.endswith(".pyc"):
                    continue
                path = Path(dirpath) / name
                info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, path.read_bytes())
                count += 1
    if count == 0:
        raise ValueError(f"{root} has no files")
    data = out.getvalue()
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError(f"{root} packs to {len(data) / 1e6:.0f} MB; projects are at most 50 MB")
    return data


def upload(transport, bundle: bytes) -> str:
    """Uploads a packed project; returns its sha256."""
    chunks = [pb.UploadBundleRequest(chunk=bundle[i:i + CHUNK_BYTES]) for i in range(0, len(bundle), CHUNK_BYTES)]
    # A fresh iterator per attempt, so a retry resends every chunk.
    return errors.call(lambda: transport.stub.UploadBundle(iter(chunks), metadata=transport._metadata,
                                                           timeout=300)).sha256


@dataclass
class Overrides:
    """What a deploy may set besides the code's own declaration (which it overrides by input name)."""

    name: str = ""
    namespace: str = ""
    python: str = ""
    triggers: dict = field(default_factory=dict)        # name: feed
    dependencies: dict = field(default_factory=dict)    # name: feed, or (feed, horizon)
    windows: dict = field(default_factory=dict)         # trigger name: 10 | "10m" | {count|duration, tumbling, all_keys}
    output: str = ""
    key: str = ""
    time: str = ""
    publication_time: str = ""
    entrypoint: str = ""
    basis: str = ""                                      # received | published
    on_restart: str = ""
    state: bool = False
    paused: bool = False
    max_error_rate: float = 0.0
    sample_events: int = 0
    allow_unverified: bool = False


def window(spec) -> pb.TransformerWindow:
    """`10` (events), `"10m"` (event time), or {"count"|"duration", "tumbling", "all_keys"}."""
    if isinstance(spec, dict):
        w = window(spec.get("count") or spec.get("duration"))
        w.tumbling = bool(spec.get("tumbling"))
        w.all_keys = bool(spec.get("all_keys"))
        return w
    if isinstance(spec, int) or (isinstance(spec, str) and spec.isdigit()):
        return pb.TransformerWindow(count=int(spec))
    return pb.TransformerWindow(duration_ns=to_duration_ns(spec))


def request(o: Overrides, *, code: str = "", bundle_sha256: str = "", validate_only: bool = False
            ) -> pb.DeployTransformerRequest:
    r = pb.DeployTransformerRequest(
        transformer=pb.TransformerRef(namespace=o.namespace, name=o.name),
        code=code,
        bundle_sha256=bundle_sha256,
        entrypoint=o.entrypoint,
        paused=o.paused,
        on_restart=o.on_restart,
        python_version=o.python,
        validate_only=validate_only,
        max_error_rate=o.max_error_rate,
        sample_events=o.sample_events,
        allow_unverified=o.allow_unverified,
        stateful=o.state,
    )
    if o.basis:
        if o.basis not in BASES:
            raise ValueError("basis must be received or published")
        r.as_of_basis = BASES[o.basis]
    for name, feed in o.triggers.items():
        r.triggers.add(name=name, feed=feed)
    for name, spec in o.windows.items():
        trigger = next((t for t in r.triggers if t.name == name), None) or r.triggers.add(name=name)
        trigger.window.CopyFrom(window(spec))
    for name, spec in o.dependencies.items():
        feed, horizon = spec if isinstance(spec, tuple) else (spec, None)
        dep = r.dependencies.add(name=name, feed=feed)
        if horizon is not None:
            dep.horizon_ns = to_duration_ns(horizon)
    if o.output or o.key or o.time or o.publication_time:
        r.output.CopyFrom(pb.TransformerOutput(feed=o.output, key_field=o.key, time_field=o.time,
                                               publication_time_field=o.publication_time))
    return r


def start(transport, path: str | Path, overrides: Overrides, *, validate_only: bool = False,
          on_message: Callable[[str], None] = lambda m: None) -> pb.TransformerBuild:
    """Uploads `path` (a project directory, or one .py file sent as code) and starts its build."""
    path = Path(path)
    if path.is_file():
        req = request(overrides, code=path.read_text(), validate_only=validate_only)
    elif path.is_dir():
        bundle = pack(path)
        on_message(f"uploading {path} ({len(bundle) / 1024:,.0f} KB)")
        req = request(overrides, bundle_sha256=upload(transport, bundle), validate_only=validate_only)
    else:
        raise FileNotFoundError(f"{path}: no such project directory or file")
    return errors.call(transport.call, "DeployTransformer", req, timeout=120)


def wait_for_build(transport, build: pb.TransformerBuild, *, poll_s: float = 1.0,
                   on_phase: Callable[[pb.TransformerBuild, float], None] = lambda b, s: None,
                   on_tick: Callable[[pb.TransformerBuild, float], None] = lambda b, s: None,
                   tick_s: float = 30.0) -> pb.TransformerBuild:
    """Polls a build until it finishes, however long: verification of a stateful transformer
    replays its whole history. `on_phase` hears each change of status; `on_tick` every `tick_s`
    while nothing changes, so a long wait shows it is alive."""
    started = time.monotonic()
    last_status, last_tick = None, started
    while True:
        elapsed = time.monotonic() - started
        if build.status != last_status:
            on_phase(build, elapsed)
            last_status, last_tick = build.status, time.monotonic()
        elif time.monotonic() - last_tick >= tick_s:
            on_tick(build, elapsed)
            last_tick = time.monotonic()
        if build.status in FINISHED:
            return build
        time.sleep(poll_s)
        build = _keep_asking(lambda: transport.call("GetTransformerBuild", pb.GetTransformerBuildRequest(id=build.id)),
                             build, on_phase, started)


def wait_for_backfill(transport, build: pb.TransformerBuild, *, poll_s: float = 2.0,
                      on_progress: Callable[[pb.Transformer, float], None] = lambda t, s: None
                      ) -> pb.Transformer:
    """After a deploy is ready: waits until its version is live, i.e. a worker runs it and, for a
    stateful transformer, has replayed every trigger event (`stats.backfill_remaining` 0).
    Raises if it is failing."""
    ref = pb.TransformerRef(namespace=build.namespace, name=build.transformer)
    started = time.monotonic()
    t = None
    while True:
        t = _keep_asking(lambda: transport.call("GetTransformer", pb.GetTransformerRequest(transformer=ref)), t,
                         None, started)
        if t is None:
            time.sleep(poll_s)
            continue
        elapsed = time.monotonic() - started
        on_progress(t, elapsed)
        current = t.version >= build.transformer_version
        reported = t.last_heartbeat_at_ns > build.finished_at_ns
        if current and t.status == "failing":
            raise errors.FailedPrecondition(f"{t.name} v{t.version} is failing: {t.status_detail or t.stats.last_error}")
        if current and t.paused:
            return t
        if current and reported and t.status == "running" and t.stats.backfill_remaining == 0:
            return t
        time.sleep(poll_s)


def _keep_asking(fetch, previous, on_phase, started, retry_s: float = 2.0):
    """One poll. While the server is unavailable (restarting, e.g. a deploy of the server
    itself), the build or transformer carries on: say so once, and keep asking."""
    import grpc

    announced = False
    while True:
        try:
            return fetch()
        except grpc.RpcError as e:
            if e.code() != grpc.StatusCode.UNAVAILABLE:
                raise errors.translate(e) from None
            if not announced and on_phase is not None and previous is not None:
                waiting = pb.TransformerBuild()
                waiting.CopyFrom(previous)
                waiting.status = "server unavailable, retrying"
                on_phase(waiting, time.monotonic() - started)
            announced = True
            time.sleep(retry_s)


# ---------- Describing builds, transformers and runs ----------


def describe_build(b: pb.TransformerBuild, *, log: bool = False, lockfile: bool = False) -> list[str]:
    lines = [f"build:           {b.id}"]
    became = f" (became version {b.transformer_version})" if b.transformer_version else ""
    lines.append(f"transformer:     {b.namespace}/{b.transformer}{became}")
    detail = f" ({b.status_detail})" if b.status_detail else ""
    status = "verified (not deployed)" if b.validate_only and b.status == "ready" else b.status
    lines.append(f"status:          {status}{detail}")
    lines.append(f"python:          {b.python_version or '3.12'}")
    packages = [ln for ln in b.lockfile.splitlines() if ln.strip() and not ln.lstrip().startswith(("#", "-", " "))]
    if b.lockfile or b.environment_bytes:
        lines.append(f"environment:     {len(packages)} packages, {b.environment_bytes / 1e6:.1f} MB")
    if b.finished_at_ns and b.created_at_ns:
        lines.append(f"took:            {(b.finished_at_ns - b.created_at_ns) / 1e9:.1f} s")
    lines += describe_report(b.report_json)
    if lockfile and b.lockfile:
        lines += ["", b.lockfile]
    if log and b.log:
        lines += ["", b.log]
    return lines


def describe_report(report_json: str) -> list[str]:
    """The verification report, stage by stage, with the fixtures' results file by file."""
    try:
        report = json.loads(report_json) if report_json else {}
    except ValueError:
        return []
    stages = report.get("stages") or []
    if not stages:
        return []
    lines = ["verification:"]
    for stage in stages:
        name = stage.get("stage", "?")
        outcome = "skipped" if isinstance(stage.get("skipped"), str) else ("ok" if stage.get("ok") else "FAILED")
        detail = ""
        if name == "load":
            detail = f"{stage.get('startup_ms', '?')} ms to start, {(stage.get('memory_bytes') or 0) / 1e6:.0f} MB"
        elif name == "replay" and outcome == "skipped":
            detail = stage["skipped"]
        elif name == "replay":
            detail = (f"{stage.get('events', 0)} events, {stage.get('errors', 0)} errors, {stage.get('outputs', 0)} "
                      f"outputs, {stage.get('ms_per_event') or 0:.2f} ms/event, deterministic: "
                      f"{stage.get('deterministic')}")
        elif name == "fixtures":
            files = stage.get("files") or []
            cases = sum(f.get("cases", 0) for f in files)
            failed = sum(len(f.get("failures") or []) for f in files)
            detail = f"{len(files)} file(s), {cases} case(s), {failed} failed" if files else "no fixtures"
        lines.append(f"  {name:<10} {outcome:<8} {detail}".rstrip())
        if stage.get("error"):
            lines += ["    " + ln for ln in str(stage["error"]).splitlines()]
        for key in ("errors", "problems"):
            for e in (stage.get(key) or [])[:5]:
                lines.append(f"    - {e if isinstance(e, str) else json.dumps(e)}")
        for f in (stage.get("failures") or [])[:3]:
            lines.append(f"    event {f.get('trigger', '')}:{f.get('offset')} at {format_ns(f.get('event_time_ns') or 0)}:")
            lines += ["      " + ln for ln in (f.get("traceback") or "").splitlines()[-4:]]
        for p in (stage.get("output_problems") or [])[:5]:
            lines.append(f"    - {p.get('problem', p)}")
        if name == "fixtures":
            for f in stage.get("files") or []:
                failures = f.get("failures") or []
                mark = "ok" if not failures else f"{len(failures)} failed"
                lines.append(f"    {f.get('file')}: {f.get('cases', 0)} case(s), {mark}")
                for failure in failures[:5]:
                    got = failure.get("got", failure.get("error"))
                    lines.append(f"      line {failure.get('line')}: expected {json.dumps(failure.get('expected'))}")
                    lines.append(f"        got {json.dumps(got) if not isinstance(got, str) else got.strip()}")
    for w in report.get("warnings") or []:
        lines.append(f"  warning: {w}")
    return lines


BASIS_TEXT = {
    pb.AS_OF_BASIS_PUBLISHED: "published (as published when the trigger was; replayed in publication order)",
    pb.AS_OF_BASIS_RECEIVED: "received (what Isodrome had when the trigger arrived; replayed in arrival order)",
    pb.AS_OF_BASIS_UNSPECIFIED: "received (what Isodrome had when the trigger arrived; replayed in arrival order)",
}


def _feed_name(f: pb.FeedRef) -> str:
    org = f"{f.organization}/" if f.organization else ""
    return f"{org}{f.namespace}/{f.name}@{f.version}" if f.name else ""


def _window_text(w: pb.TransformerWindow) -> str:
    if not (w.count or w.duration_ns):
        return ""
    size = f"last {w.count} events" if w.count else f"{_duration_text(w.duration_ns)} of event time"
    return f"  window: {size}, {'tumbling' if w.tumbling else 'sliding'}, {'all keys' if w.all_keys else 'per key'}"


def _duration_text(ns: int) -> str:
    for unit, size in (("d", 86_400 * 10**9), ("h", 3_600 * 10**9), ("m", 60 * 10**9), ("s", 10**9)):
        if ns >= size and ns % size == 0:
            return f"{ns // size}{unit}"
    return f"{ns / 1e9:g}s"


def describe_transformer(t: pb.Transformer) -> list[str]:
    lines = [f"name:            {t.namespace}/{t.name}", f"version:         {t.version} (code {t.code_sha256[:12]})"]
    if t.bundle_sha256:
        lines.append(f"project:         {t.bundle_sha256[:12]} (python {t.python_version or '3.12'})")
    if t.HasField("build"):
        detail = f" ({t.build.status_detail})" if t.build.status_detail else ""
        lines.append(f"latest build:    {t.build.id} {t.build.status}{detail}")
    lines.append(f"entrypoint:      {t.entrypoint}")
    for i in t.triggers:
        lines.append(f"  trigger    {i.name:<16} {_feed_name(i.pinned) or i.feed}{_window_text(i.window)}")
    for i in t.dependencies:
        lines.append(f"  dependency {i.name:<16} {_feed_name(i.pinned) or i.feed} "
                     f"(horizon {_duration_text(i.horizon_ns or 24 * 3_600 * 10**9)})")
    if t.HasField("output"):
        o = t.output
        lines.append(f"  output     {_feed_name(o.pinned) or o.feed} (key {o.key_field or '-'}, "
                     f"time {o.time_field or 'event_time'})")
    lines.append(f"stateful:        {'yes: ctx.state, rebuilt only by replaying every trigger event' if t.stateful else 'no'}")
    lines.append(f"as of:           {BASIS_TEXT.get(t.as_of_basis, '?')}")
    lines.append(f"on restart:      {t.on_restart or 'resume'}")
    detail = f" ({t.status_detail})" if t.status_detail else ""
    lines.append(f"status:          {t.status}{' (paused)' if t.paused else ''}{detail}")
    s = t.stats
    if t.stateful or s.backfill_remaining:
        backfill = (f"{s.backfill_remaining:,} trigger events to replay before live" if s.backfill_remaining
                    else "done (live)")
        lines.append(f"backfill:        {backfill}")
        lines.append(f"ctx.state:       {s.code_state_bytes / 1e3:,.1f} KB saved")
    lines.append(f"worker:          {t.worker or '-'}")
    lines.append(f"service account: {t.service_account}")
    lines.append(f"events:          {t.events_in:,} in, {t.events_out:,} out, {t.errors:,} errors")
    lines.append(f"last event:      {format_ns(t.last_event_at_ns) if t.last_event_at_ns else 'never'}")
    lines.append(f"last heartbeat:  {format_ns(t.last_heartbeat_at_ns) if t.last_heartbeat_at_ns else 'never'}")
    lines.append("stats:")
    lines += describe_stats(s)
    return lines


def describe_stats(s: pb.TransformerStats) -> list[str]:
    lines = [
        f"  latency:        p50 {s.latency_p50_ms:.1f} ms, p95 {s.latency_p95_ms:.1f} ms, max {s.latency_max_ms:.1f} ms "
        "(receive → outputs accepted)",
        f"  python:         {s.python_ms_per_event:.3f} ms per event",
        f"  dependencies:   {s.dependency_ms_per_call:.2f} ms per call ({s.dependency_calls:,} calls), "
        f"{s.state_versions:,} versions in memory ({s.state_bytes / 1e6:.1f} MB)",
        f"  throughput:     {s.events_per_second:.1f} events/s, lag {s.lag_ms:,} ms",
        f"  process:        {s.cpu_seconds:.2f} s CPU, {s.memory_bytes / 1e6:.1f} MB peak memory",
    ]
    if s.run_seconds:
        lines.append(f"  run time:       {s.run_seconds:.2f} s")
    if s.last_error:
        lines.append(f"  last error:     {s.last_error}")
    return lines


def describe_run(r: pb.TransformerRun) -> list[str]:
    detail = f" {r.status_detail}" if r.status_detail else ""
    return [
        f"run:             {r.id}",
        f"transformer:     {r.transformer} v{r.version}",
        f"range:           {format_ns(r.start_ns)} → {format_ns(r.end_ns)}",
        f"into:            {_feed_name(r.output)}",
        f"status:          {r.status} ({r.progress * 100:.1f}%){detail}",
        f"events:          {r.events_in:,} in, {r.events_out:,} out, {r.errors:,} errors",
    ]


def parse_window(text: str):
    """CLI `trigger=10` / `trigger=10m`, optionally `,tumbling` `,all-keys` → (trigger, spec)."""
    name, _, spec = text.partition("=")
    if not spec:
        raise ValueError(f"{text!r}: expected trigger=10 or trigger=10m")
    size, *flags = spec.split(",")
    unknown = set(flags) - {"tumbling", "all-keys"}
    if unknown:
        raise ValueError(f"{text!r}: window flags are tumbling and all-keys")
    if not size.isdigit():
        parse_duration(size)  # validates
    return name.strip(), {"count" if size.isdigit() else "duration": int(size) if size.isdigit() else size,
                          "tumbling": "tumbling" in flags, "all_keys": "all-keys" in flags}
