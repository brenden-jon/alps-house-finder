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


if __name__ == "__main__":
    main()
