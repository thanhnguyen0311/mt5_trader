import config
from data import MT5Config
from integration import connect_mt5, disconnect_mt5
from services import place_market_order

if __name__ == "__main__":
    cfg = MT5Config(
        login=config.LOGIN,
        password=config.PASSWORD,
        server=config.SERVER,
        terminal_path=r"C:\Program Files\MetaTrader 5\terminal64.exe",  # optional
    )

    connect_mt5(cfg)

    # BUY XAUUSDm
    res = place_market_order(
        symbol="XAUUSDm",
        side="BUY",
        lot=0.01,
        sl_price=3500,   # points (price_distance = points * point)
        tp_price=5500,
        deviation=30,
        magic=20260205,
        comment="XAUUSDm test",
        filling="IOC",
    )

    print(res)

    disconnect_mt5()