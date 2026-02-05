# config.py
LOGIN = 415260060                 # your MT5 login
PASSWORD = "Danny@0311"
SERVER = "Exness-MT5Trial14"     # example: "ICMarketsSC-Demo"
TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"  # optional

SYMBOL = "XAUUSD"
TIMEFRAME = "M5"                 # M1, M5, M15, H1, H4, D1...
LOT = 0.01
SL_PIPS = 200                     # for XAUUSD you may prefer points-based; see notes
TP_PIPS = 300
DEVIATION = 20
MAGIC = 20260205
COMMENT = "py-mt5"