from data import OrderResponse
from typing import Optional, Literal
import MetaTrader5 as mt5

Side = Literal["BUY", "SELL"]

def place_market_order(
        symbol: str,
        side: Side,
        lot: float,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        deviation: int = 20,
        magic: int = 0,
        comment: str = "py-mt5",
        filling: Literal["FOK", "IOC", "RETURN"] = "IOC",
) -> OrderResponse:
    """
    Places a BUY/SELL market order.

    sl_points / tp_points are in POINTS (not "pips"):
      price_distance = points * symbol.point

    Example for XAUUSDm:
      If point=0.01 then sl_points=200 => 200*0.01 = 2.00 price distance.
    """

    # --- only allow XAUUSDm (as you requested)
    if symbol != "XAUUSDm":
        return OrderResponse(ok=False, retcode=-2, comment=f"Blocked: only XAUUSDm allowed, got {symbol}")

    info = mt5.symbol_info(symbol)
    if info is None:
        return OrderResponse(ok=False, retcode=-3, comment=f"Symbol not found: {symbol}")

    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            return OrderResponse(ok=False, retcode=-4, comment=f"symbol_select failed: {mt5.last_error()}")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return OrderResponse(ok=False, retcode=-5, comment=f"symbol_info_tick failed: {mt5.last_error()}")

    side_u = side.upper().strip()
    is_buy = side_u == "BUY"
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    price = tick.ask if is_buy else tick.bid

    # price distance from points
    sl = float(sl_price) if sl_price else 0.0
    tp = float(tp_price) if tp_price else 0.0

    filling_map = {
        "FOK": mt5.ORDER_FILLING_FOK,
        "IOC": mt5.ORDER_FILLING_IOC,
        "RETURN": mt5.ORDER_FILLING_RETURN,
    }

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": float(price),
        "sl": float(sl),
        "tp": float(tp),
        "deviation": int(deviation),
        "magic": int(magic),
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_map[filling],
    }

    result = mt5.order_send(request)
    if result is None:
        err = mt5.last_error()
        return OrderResponse(ok=False, retcode=-1, comment=f"order_send returned None: {err}", request=request)

    ok = (result.retcode == mt5.TRADE_RETCODE_DONE)

    return OrderResponse(
        ok=ok,
        retcode=int(result.retcode),
        comment=str(result.comment),
        order=int(getattr(result, "order", 0)),
        deal=int(getattr(result, "deal", 0)),
        request=request,
    )