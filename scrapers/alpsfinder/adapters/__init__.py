from .bienici import BienIciAdapter
from .greenacres import GreenAcresAdapter
from .notaires import NotairesAdapter
from .seloger import SeLogerAdapter

ADAPTERS = {
    "bienici": BienIciAdapter,
    "greenacres": GreenAcresAdapter,
    "notaires": NotairesAdapter,
    "seloger": SeLogerAdapter,  # best-effort: aborts on Datadome 403
}


def get_adapter(code: str):
    try:
        return ADAPTERS[code]()
    except KeyError:
        raise SystemExit(f"Unknown source '{code}'. Available: {', '.join(sorted(ADAPTERS))}")
