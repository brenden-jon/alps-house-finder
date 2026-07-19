import click

from . import db as dbmod
from . import communes as communes_mod


@click.group()
def main():
    """Alps house finder: scrape, score, rank French Alps property listings."""


@main.command("init-db")
def init_db_cmd():
    """Create the SQLite database and schema."""
    path = dbmod.init_db()
    click.echo(f"Database initialized at {path}")


@main.command("load-communes")
def load_communes_cmd():
    """Load/refresh the commune knowledge base from data/communes/*.yaml."""
    entries = communes_mod.load_commune_yamls()
    conn = dbmod.connect()
    n = communes_mod.upsert_communes(conn, entries)
    conn.close()
    click.echo(f"Upserted {n} communes from {communes_mod.COMMUNES_DIR}")


@main.command("scrape")
@click.option("--source", "source_codes", multiple=True, help="Source code(s); default: all")
@click.option("--commune", "commune_slugs", multiple=True, help="Commune slug(s); default: all")
def scrape_cmd(source_codes, commune_slugs):
    """Scrape listings from sources into the database."""
    from .adapters import ADAPTERS, get_adapter
    from .ingest import run_scrape

    conn = dbmod.connect()
    if commune_slugs:
        placeholders = ",".join("?" * len(commune_slugs))
        rows = conn.execute(
            f"SELECT * FROM communes WHERE slug IN ({placeholders})", commune_slugs
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM communes").fetchall()
    communes = [dict(r) for r in rows]
    if not communes:
        raise SystemExit("No communes loaded. Run `alpsfinder load-communes` first.")

    codes = source_codes or sorted(ADAPTERS)
    for code in codes:
        adapter = get_adapter(code)
        click.echo(f"Scraping {adapter.name} for {len(communes)} communes...")
        result = run_scrape(conn, adapter, communes, full_run=not commune_slugs)
        click.echo(
            f"  {code}: {result['status']} — seen {result['seen']}, new {result['new']}, "
            f"price-updates {result['updated']}, gone {result['gone']}"
            + (f" — ERROR: {result['error']}" if result["error"] else "")
        )
    conn.close()


@main.command("trends")
def trends_cmd():
    """Update DVF price trends (official transaction data) for all communes."""
    from . import trends as trends_mod

    conn = dbmod.connect()
    communes = [dict(r) for r in conn.execute("SELECT * FROM communes")]
    n = trends_mod.update_trends(conn, communes)
    conn.close()
    click.echo(f"Wrote {n} trend rows (commune x year x type)")


@main.command("score")
def score_cmd():
    """Recompute the 12 scoring dimensions for all active listings."""
    from .scoring import engine

    conn = dbmod.connect()
    n = engine.score_all(conn)
    conn.close()
    click.echo(f"Scored {n} listings")


@main.command("rank")
@click.option("--top", default=20, help="Number of listings to show")
def rank_cmd(top):
    """Print ranked listings using default weights."""
    from .scoring import engine

    conn = dbmod.connect()
    ranked = engine.compute_totals(conn)
    click.echo(f"{len(ranked)} listings pass hard filters. Top {top}:\n")
    fmt = "{:>4}  {:<5} {:<22} {:<9} {:>9} {:>9} {:>5} {:>4} {:<28}"
    click.echo(fmt.format("#", "score", "commune", "type", "price", "all-in", "m²", "bd", "title"))
    for i, l in enumerate(ranked[:top], 1):
        click.echo(fmt.format(
            i, f"{l['total_score']:.2f}", (l["commune_name"] or l["commune_name_raw"] or "?")[:22],
            l["property_type"][:9], f"{l['price_eur']//1000}k", f"{l['all_in_eur']//1000}k",
            int(l["area_m2"]) if l["area_m2"] else "?", l["bedrooms"] or "?",
            (l["title"] or "")[:28],
        ))
    conn.close()


@main.command("str-snapshot")
def str_snapshot_cmd():
    """Snapshot Airbnb market evidence (count + median nightly rates) per commune."""
    from . import str_market

    conn = dbmod.connect()
    communes = [dict(r) for r in conn.execute("SELECT * FROM communes")]
    n = str_market.snapshot_all(conn, communes)
    conn.close()
    click.echo(f"Snapshotted STR market for {n} communes")


@main.command("export")
def export_cmd():
    """Export listings/communes/meta JSON for the static dashboard."""
    from .export import export_all

    conn = dbmod.connect()
    path = export_all(conn)
    conn.close()
    click.echo(f"Exported to {path}")


@main.command("refresh")
@click.option("--with-str", is_flag=True, help="Also refresh Airbnb STR snapshots (quarterly is enough)")
def refresh_cmd(with_str):
    """Full pipeline: scrape all sources, update trends, score, export."""
    ctx = click.get_current_context()
    ctx.invoke(scrape_cmd, source_codes=(), commune_slugs=())
    ctx.invoke(trends_cmd)
    if with_str:
        ctx.invoke(str_snapshot_cmd)
    ctx.invoke(score_cmd)
    ctx.invoke(export_cmd)


if __name__ == "__main__":
    main()
