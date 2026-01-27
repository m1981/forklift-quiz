# --- ADR 008: Component Facade ---
# Decision: We expose individual components via this __init__.py.
# Rationale: This allows consumers to import from `src.components.mobile`
# without knowing the internal file structure
# (e.g., `from src.components.mobile import mobile_header`).
# It also maintains backward compatibility if we move files around internally.
# ---------------------------------

from .dashboard import mobile_dashboard
from .header import mobile_header
from .hero import mobile_hero
from .option import mobile_option
from .result import mobile_result_row

__all__ = [
    "mobile_header",
    "mobile_option",
    "mobile_result_row",
    "mobile_dashboard",
    "mobile_hero",
]
