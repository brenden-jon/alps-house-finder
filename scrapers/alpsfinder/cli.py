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
        result = run_scrape(conn, adapter, communes)
        click.echo(
            f"  {code}: {result['status']} — seen {result['seen']}, new {result['new']}, "
            f"price-updates {result['updated']}, gone {result['gone']}"
            + (f" — ERROR: {result['error']}" if result["error"] else "")
        )
    conn.close()


if __name__ == "__main__":
    main()
