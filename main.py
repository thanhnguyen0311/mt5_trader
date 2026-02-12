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

    pattern2 = r'St\s*\((\d+)\.'
    match2 = re.search(pattern2, text)
    if match:
        return match.group(1)
    if match2:
        return match2.group(1)

    return None

def extract_entry_number(text: str):
    pattern = r'Entry\s*\((\d+)\.'
    match = re.search(pattern, text)

    if match:
        return match.group(1)

    return None

def validate_price(price: str):
    # Check if the price is None or not a string as a safeguard
    if price is None or not isinstance(price, str) or not price.isdigit():
        return False


    minValue = 4000
    maxValue = 6000

    # Convert string to int and validate the range
    price_int = int(price)
    if minValue <= price_int <= maxValue:
        return True

    return False




if __name__ == "__main__":



    # while True:
    #     x, y = pyautogui.position()
    #     print(f"X={x} Y={y}", end="\r")
    #


    region = {
        "left": 500,
        "top": 150,
        "width": 700,
        "height": 720
    }

    entry = 0
    stopLoss = 0


    check = True
    while True:

        # move_sl_to_breakeven()


        with mss.mss() as sct:
            screenshot = np.array(sct.grab(region))

            img = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

            # 🔥 upscale -> OCR đọc chữ nhỏ tốt hơn
            img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            # grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # blur nhẹ (RẤT nên thêm)
            gray = cv2.GaussianBlur(gray, (3,3), 0)

            # threshold
            bw = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

            # ✅ THÊM Ở ĐÂY
            kernel = np.ones((2,2), np.uint8)
            bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, iterations=1)

            # đọc toàn bộ text
            custom_config = r'--oem 3 --psm 6'

            text = pytesseract.image_to_string(bw, config=custom_config)
            # print(text)
            extracted_sl = extract_sl_number(text)
            extracted_entry = extract_entry_number(text)


            if validate_price(extracted_sl) and validate_price(extracted_entry):

                tempSL = int(extracted_sl)
                tempENTRY = int(extracted_entry)


                if stopLoss != tempSL and entry != tempENTRY:
                    print("SL : " + str(tempSL) + " ENTRY : " + str(tempENTRY))
                    if abs(tempENTRY - tempSL) > 50:
                        print("Wrong SL and ENTRY. Continue...")
                        continue

                    if check :
                        check = False
                        print("SL : " + str(tempSL) + " ENTRY : " + str(tempENTRY))
                        print("Waiting for next trade...")
                        stopLoss = tempSL
                        entry = tempENTRY
                        continue

                    if not can_place_order():
                        print("Quá 5 lệnh trong 5 phút → skip")
                        break   # bỏ vòng này, không thoát bot

                    connect_mt5(config.WORKERS[0])
                    order_generator(
                        symbol="XAUUSD",
                        sl_price=tempSL,
                        entry_price=tempENTRY,
                        lot=1
                    )

                    stopLoss = tempSL
                    entry = tempENTRY
                    continue





