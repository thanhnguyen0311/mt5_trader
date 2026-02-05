from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any

@dataclass
class OrderResponse:
    ok: bool
    retcode: int
    comment: str
    order: int = 0
    deal: int = 0
    request: Optional[Dict[str, Any]] = None


@dataclass
class MT5Config:
    login: int
    password: str
    server: str
    terminal_path: Optional[str] = None  # optional: path to terminal64.exe