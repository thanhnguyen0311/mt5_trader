import config
from data import MT5Config
from integration import connect_mt5, disconnect_mt5
from services import place_market_order, close_all_positions, order_generator, move_sl_to_breakeven
import pyautogui
import time
import re
import MetaTrader5 as mt5

import mss
import numpy as np
import cv2
import pytesseract
import os


pytesseract.pytesseract.tesseract_cmd = r"Tesseract-OCR\tesseract.exe"

os.environ["TESSDATA_PREFIX"] = r"Tesseract-OCR\tessdata"

order_times = []
FIVE_MINUTES = 5 * 60
MAX_ORDERS = 5
def can_place_order():
    global order_times  # Khai báo biến toàn cục

    now = time.time()
    order_times = [t for t in order_times if now - t <= FIVE_MINUTES]

    if len(order_times) >= MAX_ORDERS:
        return False

    order_times.append(now)
    return True


def extract_sl_number(text: str):
    pattern = r'SL\s*\((\d+)\.'
    match = re.search(pattern, text)

    if match:
        return match.group(1)

    return None

def extract_ENTRY_number(text: str):
    pattern = r'Entry\s*\((\d+)\.'
    match = re.search(pattern, text)

    if match:
        return match.group(1)

    return None

def validate_price(price: str):
    # Check if the price is None or not a string as a safeguard
    if price is None or not isinstance(price, str) or not price.isdigit():
        return False


    minValue = 1000
    maxValue = 150000

    # Convert string to int and validate the range
    price_int = int(price)
    if minValue <= price_int <= maxValue:
        return True

    return False




if __name__ == "__main__":
    cfg = MT5Config(
        login=config.LOGIN,
        password=config.PASSWORD,
        server=config.SERVER,
        terminal_path=r"C:\Program Files\MetaTrader 5\terminal64.exe",  # optional
    )



    region = {
        "left": 10,
        "top": 170,
        "width": 1200,
        "height": 700
    }
    entry = 0
    stopLoss = 0
    connect_mt5(cfg)


    check = True
    while True:

        move_sl_to_breakeven()


        with mss.mss() as sct:
            screenshot = np.array(sct.grab(region))

            img = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

            # 🔥 upscale -> OCR đọc chữ nhỏ tốt hơn
            img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            # grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # threshold
            gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

            # đọc toàn bộ text
            custom_config = r'--oem 3 --psm 6'

            text = pytesseract.image_to_string(gray, config=custom_config)
            # print(text)
            extracted_sl = extract_sl_number(text)
            extracted_entry = extract_ENTRY_number(text)


            if validate_price(extracted_sl) and validate_price(extracted_entry):
                tempSL = int(extracted_sl)
                tempENTRY = int(extracted_entry)


                if stopLoss != tempSL and entry != tempENTRY:
                    if check :
                        check = False
                        print("SL : " + str(tempSL) + " ENTRY : " + str(tempENTRY))
                        print("Waiting for next trade...")
                        stopLoss = tempSL
                        entry = tempENTRY
                        continue
                    print("Stop Loss : " + str(tempSL) + " Entry : " + str(tempENTRY) + "")
                    if mt5.positions_get():
                        close_all_positions()

                    if not can_place_order():
                        print("Quá 5 lệnh trong 5 phút → skip")
                        break   # bỏ vòng này, không thoát bot

                    if 150000 > int(tempSL) > 10000 and 150000> int(tempENTRY) > 10000:
                        print("BTC")
                        order_generator(
                            symbol="BTCUSDc",
                            sl_price=tempSL,
                            lot=0.5
                        )
                        stopLoss = tempSL
                        entry = tempENTRY
                        continue

                    if 1000 < int(tempSL) < 7000 and 1000 < int(tempENTRY) < 7000:
                        print("XAU")
                        order_generator(
                            symbol="XAUUSDc",
                            sl_price=tempSL,
                            lot=0.25
                        )
                        stopLoss = tempSL
                        entry = tempENTRY
                        continue


            time.sleep(1)



