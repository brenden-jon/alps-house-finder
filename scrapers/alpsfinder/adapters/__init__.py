from .bienici import BienIciAdapter

ADAPTERS = {
    "bienici": BienIciAdapter,
}


def get_adapter(code: str):
    try:
        return ADAPTERS[code]()
    except KeyError:
        raise SystemExit(f"Unknown source '{code}'. Available: {', '.join(sorted(ADAPTERS))}")
