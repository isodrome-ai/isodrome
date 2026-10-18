"""`transformer …`: Python that Isodrome runs on feeds' events to write a feed, live or over past
events (a backtest run)."""

from __future__ import annotations

import time

import click

from isodrome import deploy
from isodrome.cli.context import Context, pass_context
from isodrome.parse import format_ns, parse_time
from isodrome.v1 import isodrome_pb2 as pb


def _ref(name: str, namespace: str | None) -> pb.TransformerRef:
    return pb.TransformerRef(namespace=namespace or "", name=name)


def _echo(lines) -> None:
    for line in lines:
        click.echo(line)


@click.group()
def transformer() -> None:
    """Deploy, test, inspect and backtest transformers.

    A transformer is Python that Isodrome runs on its triggers' events to write a feed. With the
    published basis (`as_of="published"`), triggers replay in publication order and each sees
    what had been published by then; with received (the default), in arrival order, seeing what
    Isodrome had received. Either way a backtest computes exactly what live did.
    """


def _deploy_options(f):
    options = [
        click.argument("path", default=".", type=click.Path(exists=True)),
        click.option("--name", default="", help="Which transformer (a project may declare several)."),
        click.option("-n", "--namespace", default="", help="Its namespace (default: your key's)."),
        click.option("--python", "python_version", type=click.Choice(["3.12", "3.13"]), help="Default 3.12."),
        click.option("--state", is_flag=True,
                     help="The code keeps ctx.state (also @iso.transformer(state=True)): each version first "
                          "replays every trigger event."),
        click.option("--trigger", "triggers", multiple=True, help="Override: name=[org/]namespace/feed[@v|:tag]."),
        click.option("--dependency", "dependencies", multiple=True,
                     help="Override: name=feed[,horizon=24h] (horizons up to 400d)."),
        click.option("--window", "windows", multiple=True, help="trigger=10 or trigger=10m[,tumbling][,all-keys]."),
        click.option("--basis", type=click.Choice(["received", "published"]),
                     help="What triggers see: what Isodrome had received, or what had been published."),
        click.option("--output", default="", help="Override the output feed."),
        click.option("--key", default="", help="Override the output's key field."),
        click.option("--time", "time_field", default="", help="Override the output's time field."),
        click.option("--publication-time", default="", help="Override the output's publication time field."),
        click.option("--entrypoint", default="", help="module:function (a single file: the function)."),
        click.option("--on-restart", type=click.Choice(["resume", "latest"])),
        click.option("--paused", is_flag=True, help="Deploy without starting it."),
        click.option("--max-error-rate", default=0.0, help="Verification: share of replayed events allowed to raise."),
        click.option("--sample-events", default=0, help="Verification: recent events per trigger to replay (default 1,000)."),
        click.option("--allow-unverified", is_flag=True, help="Skip replaying recent data (load, checks and fixtures still run)."),
        click.option("--no-wait", is_flag=True, help="Return once the build has started."),
    ]
    for option in reversed(options):
        f = option(f)
    return f


def _overrides(kw) -> deploy.Overrides:
    def pairs(values, what):
        out = {}
        for text in values:
            name, _, rest = text.partition("=")
            if not rest:
                raise click.BadParameter(f"{text!r}: expected name=feed", param_hint=what)
            out[name.strip()] = rest.strip()
        return out

    dependencies = {}
    for name, rest in pairs(kw["dependencies"], "--dependency").items():
        feed, _, options = rest.partition(",")
        horizon = None
        for option in filter(None, options.split(",")):
            key, _, value = option.partition("=")
            if key != "horizon":
                raise click.BadParameter(f"{option!r}: dependency options are horizon=DURATION", param_hint="--dependency")
            horizon = value
        dependencies[name] = (feed, horizon)
    try:
        windows = dict(deploy.parse_window(w) for w in kw["windows"])
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="--window") from None
    return deploy.Overrides(
        name=kw["name"], namespace=kw["namespace"], python=kw["python_version"] or "",
        triggers=pairs(kw["triggers"], "--trigger"), dependencies=dependencies, windows=windows,
        output=kw["output"], key=kw["key"], time=kw["time_field"], publication_time=kw["publication_time"],
        entrypoint=kw["entrypoint"], basis=kw["basis"] or "", on_restart=kw["on_restart"] or "",
        state=kw["state"], paused=kw["paused"], max_error_rate=kw["max_error_rate"],
        sample_events=kw["sample_events"], allow_unverified=kw["allow_unverified"],
    )


def _phase(build: pb.TransformerBuild, elapsed: float) -> None:
    detail = f" ({build.status_detail})" if build.status_detail else ""
    click.echo(f"  {elapsed:>6.1f} s  {build.status}{detail}", err=True)


def _tick(build: pb.TransformerBuild, elapsed: float) -> None:
    hint = " (verifying a stateful transformer replays its whole history)" if build.status == "verifying" else ""
    click.echo(f"  {elapsed:>6.1f} s  still {build.status}{hint}", err=True)


def _run_deploy(ctx: Context, validate_only: bool, kw) -> None:
    client = ctx.client()
    overrides = _overrides(kw)
    try:
        build = deploy.start(client, kw["path"], overrides, validate_only=validate_only,
                             on_message=lambda m: click.echo(m, err=True))
    except (ValueError, FileNotFoundError) as e:
        raise click.ClickException(str(e)) from None
    click.echo(f"build {build.id} {build.status}")
    if kw["no_wait"]:
        return
    build = deploy.wait_for_build(client, build, on_phase=_phase, on_tick=_tick)
    _echo(deploy.describe_build(build))
    if build.status != "ready":
        raise click.ClickException(f"{build.status}: {build.status_detail or 'see the report above'}")
    if validate_only or kw["paused"]:
        return
    click.echo(f"{build.transformer} v{build.transformer_version} deployed; waiting for it to go live", err=True)
    last = {"remaining": None, "at": float("-inf")}  # the first count always shows

    def progress(t: pb.Transformer, elapsed: float) -> None:
        remaining = t.stats.backfill_remaining
        if remaining and (remaining != last["remaining"]) and time.monotonic() - last["at"] >= 5:
            click.echo(f"  {elapsed:>6.1f} s  backfill: {remaining:,} trigger events to replay", err=True)
            last.update(remaining=remaining, at=time.monotonic())

    try:
        t = deploy.wait_for_backfill(client, build, on_progress=progress)
    except Exception as e:  # failing: say so, with what the transformer reports
        raise click.ClickException(str(e)) from None
    if t.paused:
        click.echo(f"{t.name} v{t.version} is paused")
    else:
        click.echo(f"{t.name} v{t.version} is live ({t.events_in:,} events in, {t.events_out:,} out)")


@transformer.command("deploy")
@_deploy_options
@pass_context
def transformer_deploy(ctx: Context, **kw) -> None:
    """Deploy a project (a directory whose code declares transformers with @iso.transformer) or
    a single .py file (admin keys only).

    Isodrome installs its requirements, verifies it on recent data and the project's fixtures,
    and only then makes it the new version; a failed build never changes the running one. This
    waits through the build's phases and then, for a stateful transformer, its backfill (every
    trigger event replayed before it goes live), however long that takes.
    """
    _run_deploy(ctx, False, kw)


@transformer.command("test")
@_deploy_options
@pass_context
def transformer_test(ctx: Context, **kw) -> None:
    """Build and verify a project exactly like deploy, without deploying it. Prints the
    verification report: load, static checks, a replay of recent events, and the fixtures
    (isodrome_tests/*.jsonl, and isodrome_tests/<transformer>/*.jsonl for one transformer)."""
    _run_deploy(ctx, True, kw)


@transformer.command("list")
@pass_context
def transformer_list(ctx: Context) -> None:
    """The organization's transformers."""
    transformers = ctx.client().call("ListTransformers", pb.ListTransformersRequest()).transformers
    if not transformers:
        click.echo("(no transformers)")
    for t in transformers:
        state = "stateful" if t.stateful else ""
        backfill = f"backfill {t.stats.backfill_remaining:,} to go" if t.stats.backfill_remaining else ""
        detail = "  ".join(x for x in (state, backfill, t.status_detail) if x)
        click.echo(f"{t.namespace + '/' + t.name:<28} v{t.version:<3} {t.status:<8} {t.events_in:>10,} in "
                   f"{t.events_out:>10,} out {t.errors:>6,} errors  {detail}".rstrip())


@transformer.command("show")
@click.argument("name")
@click.option("-n", "--namespace", default="")
@click.option("--code", is_flag=True, help="Print the code too (single-file transformers).")
@pass_context
def transformer_show(ctx: Context, name, namespace, code) -> None:
    """A transformer: inputs, basis, state, status and runtime statistics."""
    t = ctx.client().call("GetTransformer", pb.GetTransformerRequest(transformer=_ref(name, namespace)))
    _echo(deploy.describe_transformer(t))
    if code and t.code:
        click.echo("\n" + t.code)


@transformer.command("builds")
@click.argument("name")
@click.option("-n", "--namespace", default="")
@pass_context
def transformer_builds(ctx: Context, name, namespace) -> None:
    """A transformer's builds."""
    builds = ctx.client().call("ListTransformerBuilds",
                               pb.ListTransformerBuildsRequest(transformer=_ref(name, namespace))).builds
    for b in builds:
        click.echo(f"{b.id}  {format_ns(b.created_at_ns)}  {b.status:<20} {b.status_detail}".rstrip())


@transformer.command("build")
@click.argument("build_id")
@click.option("--log", is_flag=True)
@click.option("--lockfile", is_flag=True)
@pass_context
def transformer_build(ctx: Context, build_id, log, lockfile) -> None:
    """One build: status, verification report; --lockfile, --log."""
    b = ctx.client().call("GetTransformerBuild", pb.GetTransformerBuildRequest(id=build_id))
    _echo(deploy.describe_build(b, log=log, lockfile=lockfile))


@transformer.command("pause")
@click.argument("name")
@click.option("-n", "--namespace", default="")
@pass_context
def transformer_pause(ctx: Context, name, namespace) -> None:
    t = ctx.client().call("PauseTransformer", pb.PauseTransformerRequest(transformer=_ref(name, namespace)))
    click.echo(f"Paused {t.namespace}/{t.name}.")


@transformer.command("resume")
@click.argument("name")
@click.option("-n", "--namespace", default="")
@pass_context
def transformer_resume(ctx: Context, name, namespace) -> None:
    t = ctx.client().call("ResumeTransformer", pb.ResumeTransformerRequest(transformer=_ref(name, namespace)))
    click.echo(f"Resumed {t.namespace}/{t.name} ({t.on_restart or 'resume'} on restart).")


@transformer.command("delete")
@click.argument("name")
@click.option("-n", "--namespace", default="")
@click.option("-y", "--yes", is_flag=True)
@pass_context
def transformer_delete(ctx: Context, name, namespace, yes) -> None:
    """Delete a transformer; its runs are cancelled, its feeds and data stay."""
    if not yes:
        click.confirm(f"Delete transformer {name}? (Its feeds and data stay.)", abort=True, err=True)
    ctx.client().call("DeleteTransformer", pb.DeleteTransformerRequest(transformer=_ref(name, namespace)))
    click.echo(f"Deleted transformer {name}; its feeds and data stay.")


@transformer.command("run")
@click.argument("name")
@click.option("--from", "start", required=True, help="Trigger events' event time from (a date, RFC 3339 or ns).")
@click.option("--to", "end", required=True, help="To (exclusive).")
@click.option("--into", default="", help="The feed it writes (default NAME_run; an existing one gets a new version).")
@click.option("-n", "--namespace", default="")
@click.option("--wait/--no-wait", default=True, help="Wait for it to finish, showing progress (default).")
@pass_context
def transformer_run(ctx: Context, name, start, end, into, namespace, wait) -> None:
    """A backtest: replays the triggers' events in [--from, --to) exactly as live saw them
    (received: in arrival order; published: in publication order), a stateful transformer's
    state warmed up from the first trigger event, into its own feed."""
    try:
        start_ns, end_ns = parse_time(start), parse_time(end)
    except ValueError as e:
        raise click.BadParameter(str(e)) from None
    client = ctx.client()
    run = client.call("StartTransformerRun", pb.StartTransformerRunRequest(
        transformer=_ref(name, namespace), start_ns=start_ns, end_ns=end_ns, into=into))
    click.echo(f"Started run {run.id} of {run.transformer} v{run.version} into {deploy._feed_name(run.output)}")
    if not wait:
        return
    started, last = time.monotonic(), None
    while run.status not in ("done", "failed", "cancelled"):
        time.sleep(1)
        run = client.call("GetTransformerRun", pb.GetTransformerRunRequest(id=run.id))
        shown = (run.status, round(run.progress, 2))
        if shown != last:
            click.echo(f"  {time.monotonic() - started:>6.1f} s  {run.status:<9} {run.progress * 100:5.1f}%  "
                       f"{run.events_in:,} in, {run.events_out:,} out, {run.errors:,} errors", err=True)
            last = shown
    _echo(deploy.describe_run(run))
    if run.status != "done":
        raise click.ClickException(f"run {run.status}: {run.status_detail}")


@transformer.command("runs")
@click.argument("name")
@click.option("-n", "--namespace", default="")
@pass_context
def transformer_runs(ctx: Context, name, namespace) -> None:
    """A transformer's runs."""
    for r in ctx.client().call("ListTransformerRuns",
                               pb.ListTransformerRunsRequest(transformer=_ref(name, namespace))).runs:
        click.echo(f"{r.id}  v{r.version:<3} {r.status:<9} {r.progress * 100:5.1f}%  {format_ns(r.start_ns)} → "
                   f"{format_ns(r.end_ns)}  into {deploy._feed_name(r.output)}  {r.events_in:,} in {r.events_out:,} out")


@transformer.command("run-show")
@click.argument("run_id")
@pass_context
def transformer_run_show(ctx: Context, run_id) -> None:
    _echo(deploy.describe_run(ctx.client().call("GetTransformerRun", pb.GetTransformerRunRequest(id=run_id))))


@transformer.command("run-cancel")
@click.argument("run_id")
@pass_context
def transformer_run_cancel(ctx: Context, run_id) -> None:
    r = ctx.client().call("CancelTransformerRun", pb.CancelTransformerRunRequest(id=run_id))
    click.echo(f"Run {r.id} is {r.status}.")
