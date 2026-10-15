"""Public feeds and namespaces, service accounts and connectors, against the fake server."""

import json

from isodrome.config import Config
from isodrome.v1 import isodrome_pb2 as pb


def _setup(iso, fake):
    """acme: default/trades (org-only) and markets/quotes (public); isodrome: public/forecasts."""
    iso("feed", "create", "trades")
    iso("namespace", "create", "markets", "--public")
    iso("feed", "create", "markets/quotes")
    fake.add_public_feed()


def _listed(result):
    return {row["feed"]: row for row in map(json.loads, result.stdout.splitlines())}


def test_feed_list_spans_namespaces_and_organizations(iso, fake):
    _setup(iso, fake)
    result = iso("feed", "list")
    assert result.exit_code == 0, result.output
    lines = result.stdout.splitlines()
    assert lines[0].split()[:3] == ["feed", "access", "key"]
    assert any(line.startswith("default/trades ") and " org " in line for line in lines)
    assert any(line.startswith("markets/quotes ") and " public " in line for line in lines)
    assert any(line.startswith("isodrome/public/forecasts ") and "public, read-only" in line for line in lines)

    rows = _listed(iso("feed", "list", "-o", "json"))
    assert {f: r["access"] for f, r in rows.items()} == {
        "default/trades": "org", "markets/quotes": "public", "isodrome/public/forecasts": "public, read-only",
    }
    assert rows["isodrome/public/forecasts"]["description"] == "Point forecasts"
    assert set(_listed(iso("feed", "list", "--mine", "-o", "json"))) == {"default/trades", "markets/quotes"}
    assert set(_listed(iso("feed", "list", "--public", "-o", "json"))) == {
        "markets/quotes", "isodrome/public/forecasts",
    }
    assert set(_listed(iso("feed", "list", "-n", "isodrome/public", "-o", "json"))) == {"isodrome/public/forecasts"}


def test_namespace_list_and_publishing(iso, fake):
    _setup(iso, fake)
    lines = iso("namespace", "list").stdout.splitlines()
    assert any(line.split()[:3] == ["*", "default", "org"] for line in lines)
    assert any(line.split()[:2] == ["markets", "public"] for line in lines)
    assert any(line.split()[:3] == ["isodrome/public", "public,", "read-only"] for line in lines)
    assert iso("namespace", "update", "markets", "--private").exit_code == 0
    assert "markets" not in fake.public_namespaces
    assert iso("namespace", "update", "markets").exit_code == 2  # neither --public nor --private


def test_reading_another_organizations_feed(iso, fake):
    _setup(iso, fake)
    shown = iso("feed", "show", "isodrome/public/forecasts")
    assert shown.exit_code == 0, shown.output
    assert "public, read-only (isodrome)" in shown.output and "attribution: Copyright Met Éireann" in shown.output
    described = iso("feed", "describe", "isodrome/public/forecasts").output
    assert "read-only: isodrome publishes it" in described and "iso feed push" not in described

    result = iso("feed", "query", "isodrome/public/forecasts", "-o", "json")
    assert json.loads(result.stdout.splitlines()[0])["price"] == 7.5
    assert "Data: Copyright Met Éireann" in result.stderr  # credit, apart from the data
    assert fake.last_read.feed.organization == "isodrome"


def test_using_another_organizations_namespace(iso, fake):
    _setup(iso, fake)
    assert iso("namespace", "use", "isodrome/nope").exit_code == 1
    assert iso("namespace", "use", "isodrome/public").exit_code == 0
    assert Config.load().profile().namespace == "isodrome/public"
    assert iso("feed", "query", "forecasts", "--count").stdout.strip() == "1"
    assert (fake.last_read.feed.organization, fake.last_read.feed.namespace) == ("isodrome", "public")
    # Own feeds stay reachable by namespace/feed.
    assert iso("feed", "show", "default/trades").exit_code == 0


def test_another_organizations_feeds_cannot_be_changed(iso, fake):
    _setup(iso, fake)
    creates = fake.requests.count("CreateFeed")
    for args in (
        ("feed", "push", "isodrome/public/forecasts", "--data", "{}"),
        ("feed", "create", "isodrome/public/mine"),
        ("feed", "delete", "isodrome/public/forecasts", "-y"),
        ("feed", "update", "isodrome/public/forecasts", "--description", "x"),
    ):
        result = iso(*args)
        assert result.exit_code == 1 and "can be read, but not changed" in result.output, args
    assert fake.requests.count("CreateFeed") == creates  # refused before reaching the server
    # Naming your own organization explicitly is fine.
    assert iso("feed", "create", "acme/default/mine").exit_code == 0


def test_feed_references(iso, fake):
    _setup(iso, fake)
    assert iso("feed", "show", "a/b/c/d").exit_code == 2
    assert iso("feed", "show", "markets/quotes", "-n", "default").exit_code == 2
    assert iso("feed", "show", "quotes", "-n", "markets").exit_code == 0


def test_query_time_options(iso, fake):
    _setup(iso, fake)
    iso("feed", "query", "isodrome/public/forecasts", "--as-of", "now", "--as-of-basis", "published",
        "--dedupe", "_key", "--dedupe-order", "publication")
    read = fake.last_read
    assert read.as_of_basis == pb.AS_OF_BASIS_PUBLISHED
    assert (list(read.dedupe.columns), read.dedupe.order) == (["_key"], pb.DEDUPE_ORDER_PUBLICATION)


def test_feed_provenance_options(iso, fake):
    assert iso("feed", "create", "rates", "--licence", "CC BY 4.0", "--attribution", "ECB").exit_code == 0
    feed = fake.feeds[("default", "rates")]
    assert (feed.licence, feed.attribution) == ("CC BY 4.0", "ECB")


def test_service_accounts(iso, fake):
    assert iso("service-account", "create", "ci", "--role", "writer").exit_code == 0
    assert "ci " in iso("service-account", "list").output
    assert iso("key", "create", "--role", "writer", "--service-account", "ci").exit_code == 0
    request = fake.last_key_request
    assert (request.service_account, request.personal) == ("ci", False)
    assert iso("key", "create", "--role", "writer", "--service-account", "ci", "--organization").exit_code == 2


def test_connectors(iso, fake):
    templates = iso("connector", "templates", "--details").output
    assert "met_eireann.point_forecast" in templates and "licence: CC BY 4.0" in templates
    assert iso("connection", "create", "dublin", "--template", "met_eireann.point_forecast",
               "--options", "not json").exit_code == 2
    created = iso("connection", "create", "dublin", "--template", "met_eireann.point_forecast", "--paused")
    assert created.exit_code == 0 and "service account connection-dublin" in created.output
    assert "dublin" in iso("connection", "list").output
