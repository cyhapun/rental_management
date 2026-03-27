from __future__ import annotations

from typing import Any


def money(v: Any) -> str:
    """
    Format tiền theo kiểu Việt Nam: 1.234.567
    """
    if v is None:
        return "0"
    try:
        n = int(float(v))
    except Exception:
        return str(v)
    return f"{n:,}".replace(",", ".")

