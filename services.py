import time

from typing import Optional, Literal, List, Dict, Any
import MetaTrader5 as mt5

from data import OrderResponse

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
    # Giá khớp thực tế (nếu có)
    fill_price = float(getattr(result, "price", 0.0) or 0.0)

    # nếu broker không trả price, fallback sang tick hiện tại
    if ok and (fill_price <= 0):
        t2 = mt5.symbol_info_tick(symbol)
        if t2:
            fill_price = float(t2.ask if is_buy else t2.bid)


    return OrderResponse(
        ok=ok,
        retcode=int(result.retcode),
        comment=str(result.comment),
        order=int(getattr(result, "order", 0)),
        deal=int(getattr(result, "deal", 0)),
        fill_price=fill_price,
        request=request
    )


def close_all_positions(symbol=None):

    positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()

    if not positions:
        return

    print(f"\n🔥 Found {len(positions)} positions. Closing...\n")

    for pos in positions:

        tick = mt5.symbol_info_tick(pos.symbol)

        if pos.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
            side = "BUY"
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
            side = "SELL"

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "position": pos.ticket,
            "volume": pos.volume,
            "type": order_type,
            "price": price,
            "deviation": 30,
            "magic": pos.magic,
            "comment": "close_all",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ CLOSED | {pos.symbol} | Ticket: {pos.ticket} | {side} | Vol: {pos.volume}")
        else:
            print(f"❌ FAILED | Ticket: {pos.ticket} | retcode={result.retcode if result else 'None'}")

    print("\n🚀 Done closing positions.\n")


def _retry_place_until_ok(
        *,
        symbol: str,
        side: Side,
        lot: float,
        sl: float,
        tp: float,
        deviation: int = 20,
        magic: int = 0,
        comment: str = "py-mt5",
        filling: Literal["FOK", "IOC", "RETURN"] = "IOC",
        retry_delay_sec: float = 0.0,  # 0 = retry ngay lập tức
) -> OrderResponse:
    """
    Retry tới khi MT5 retcode DONE.
    Dừng nếu gặp lỗi wrapper "fatal": -1, -3, -4, -5 (để tránh loop vô hạn khi MT5/symbol/tick lỗi).
    """
    while True:
        resp = place_market_order(
            symbol=symbol,
            side=side,
            lot=lot,
            sl_price=sl,
            tp_price=tp,
            deviation=deviation,
            magic=magic,
            comment=comment,
            filling=filling,
        )
        if resp.ok:
            return resp

        # Fatal errors from wrapper -> stop
        if resp.retcode in (-1, -3, -4, -5):
            return resp

        if retry_delay_sec > 0:
            time.sleep(retry_delay_sec)

def order_generator(
        symbol: str,
        lot: float,
        sl_price: float,
        *,
        rr_targets=(1.25, 2.5, 4.0),  # TP1=1R, TP2=2R, TP3=3R
        deviation: int = 20,
        magic: int = 0,
        filling: Literal["FOK", "IOC", "RETURN"] = "IOC",
) -> Dict[str, Any]:
    """
    - Nếu sl < entry => BUY, else SELL
    - Tạo 3 lệnh market (TP1/TP2/TP3), SL giống nhau
    - Retry ngay lập tức cho tới khi khớp (DONE)
    """
    sl = float(sl_price)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {
            "ok": False,
            "error": f"symbol_info_tick failed for {symbol}: {mt5.last_error()}",
            "side": None,
            "orders": [],
            "tps": [],
        }

    sym_u = symbol.upper()
    ask = float(getattr(tick, "ask", 0.0) or 0.0)
    bid = float(getattr(tick, "bid", 0.0) or 0.0)
    last = float(getattr(tick, "last", 0.0) or 0.0)

    if ask <= 0 or bid <= 0:
        return {
            "ok": False,
            "error": f"Invalid tick prices for {symbol}: ask={ask}, bid={bid}",
            "side": None,
            "orders": [],
            "tps": [],
        }

    mid = last if last > 0 else (ask + bid) / 2.0
    # side dựa trên SL so với giá hiện tại (mid)
    side: Side = "BUY" if sl < mid else "SELL"
    # entry thật dùng ask/bid theo side
    entry = ask if side == "BUY" else bid
    # ---- 2) Áp giới hạn chênh lệch SL so với entry theo symbol ----
    max_diff: Optional[float] = None
    if "BTC" in sym_u:
        max_diff = 500.0
        sl = sl - 30.0
    elif "XAU" in sym_u:
        max_diff = 50.0
        if side == "BUY":
            sl = sl - 3
        else:
            sl = sl + 3

    if max_diff is not None:
        diff = abs(entry - sl)
        if diff > max_diff:
            # kéo SL về cách entry đúng max_diff, giữ đúng hướng
            old_sl = sl
            if side == "BUY":
                sl = entry - max_diff
            else:
                sl = entry + max_diff

            print(f"⚠️ SL too far for {symbol}: {diff:.2f} > {max_diff:.2f}  -> Adjust SL {old_sl} -> {sl}")

    # ---- 3) Tính R và TP ----
    r = abs(entry - sl)
    if r <= 0:
        return {
            "ok": False,
            "error": "Invalid risk: entry_price must be different from sl_price",
            "side": None,
            "orders": [],
            "tps": [],
        }
    side: Side = "BUY" if sl < entry else "SELL"
    # TP theo R-multiple từ entry
    if side == "BUY":
        tps = [entry + r * float(m) for m in rr_targets]
    else:
        tps = [entry - r * float(m) for m in rr_targets]

    lot_each = float(lot)

    orders: List[OrderResponse] = []
    all_ok = True
    fill_prices: List[float] = []


    for i, tp in enumerate(tps, start=1):
        resp = _retry_place_until_ok(
            symbol=symbol,
            side=side,
            lot=lot_each,
            sl=sl,
            tp=float(tp),
            deviation=deviation,
            magic=magic,
            comment=f"TP{i}",
            filling=filling,
            retry_delay_sec=0.0,
        )
        orders.append(resp)

        if resp.ok:
            fp = float(getattr(resp, "fill_price", 0.0) or 0.0)
            fill_prices.append(fp)
            print(f"✅ FILLED {symbol} | {side} | TP{i} | lot={lot_each} | Entry={fp} | SL={sl} | TP={tp}")
        else:
            all_ok = False
            print(f"❌ FAILED {symbol} | {side} | TP{i} | retcode={resp.retcode} | {resp.comment}")
            break

    # Nếu cả 3 lệnh đều ok -> in tổng kết
    if all_ok and len(fill_prices) == 3:
        entry_avg = sum(fill_prices) / 3.0
        print("\n================= ORDER SUMMARY =================")
        print(f"✅ Symbol : {symbol}")
        print(f"✅ Side   : {side}")
        print(f"✅ SL     : {sl}")
        print(f"✅ Entry  : {entry_avg}   (avg of 3 fills)")
        print(f"✅ TP1    : {tps[0]}")
        print(f"✅ TP2    : {tps[1]}")
        print(f"✅ TP3    : {tps[2]}")
        print("=================================================\n")

    return {
        "ok": all_ok,
        "side": side,
        "sl": sl,
        "entry": entry,
        "tps": tps,
        "lot_each": lot_each,
        "orders": orders,
    }



def move_sl_to_breakeven(symbol=None):
    positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()

    if not positions:
        return

    # ✅ chỉ còn đúng 1 position
    if len(positions) != 1:
        return

    pos = positions[0]

    entry_price = pos.price_open
    current_sl = pos.sl

    # tránh spam modify nếu SL đã ở BE hoặc cao hơn
    if current_sl == entry_price:
        return

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": pos.symbol,
        "position": pos.ticket,
        "sl": entry_price,   # 🔥 Move to BE
        "tp": pos.tp,        # giữ TP cũ
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print("🔥 SL moved to BREAKEVEN!")
        print(f"Symbol : {pos.symbol}")
        print(f"Entry  : {entry_price}")
        print(f"New SL : {entry_price}")

    else:
        print("❌ Failed to modify SL")
        print("retcode:", result.retcode if result else "None")