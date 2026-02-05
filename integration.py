import MetaTrader5 as mt5

from data import MT5Config


def connect_mt5(cfg: MT5Config) -> None:
    """
    Connects to MetaTrader 5 terminal.
    MT5 terminal must be installed and the account must be valid.
    """
    if cfg.terminal_path:
        ok = mt5.initialize(cfg.terminal_path, login=cfg.login, password=cfg.password, server=cfg.server)
    else:
        ok = mt5.initialize(login=cfg.login, password=cfg.password, server=cfg.server)

    if not ok:
        raise RuntimeError(f"mt5.initialize() failed: {mt5.last_error()}")

    acc = mt5.account_info()
    if acc is None:
        raise RuntimeError(f"mt5.account_info() failed: {mt5.last_error()}")

    # Optional print
    print(f"Connected MT5: login={acc.login}, balance={acc.balance}, equity={acc.equity}")


def disconnect_mt5() -> None:
    mt5.shutdown()