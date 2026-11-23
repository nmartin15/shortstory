"""Style bible and IP safety gate."""

from .bible import StyleBible, load_style_bible
from .ip_gate import IPGateResult, check_ip_safety, require_ip_safe

__all__ = [
    "IPGateResult",
    "StyleBible",
    "check_ip_safety",
    "load_style_bible",
    "require_ip_safe",
]
