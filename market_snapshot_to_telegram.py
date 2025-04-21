# market_snapshot_to_telegram.py
# -------------------------------------------------- #
import yfinance as yf
import requests, os, time
from datetime import datetime as dt
import pytz

# --------- Tickers & ตลาด ------------------------- #
TICKERS = {
    "DOW":    "^DJI",
    "GOLD":   "GC=F",
    "BTC":    "BTC-USD",
    "HSI":    "^HSI",
    "NIKKEI": "^N225",
    "SET":    "^SET.BK",
}

# เวลาเปิด‑ปิด (regular session คร่าว ๆ)
MARKET_HOURS = {
    "DOW":    {"tz": "US/Eastern",   "open": (9, 30), "close": (16, 0)},
    "HSI":    {"tz": "Asia/Hong_Kong","open": (9, 30), "close": (16, 0)},
    "NIKKEI": {"tz": "Asia/Tokyo",    "open": (9, 0), "close": (15, 0)},
    "SET":    {"tz": "Asia/Bangkok",  "open": (10,0), "close": (16,30)},
    "GOLD":   {"tz": "US/Eastern",    "open": (18,0), "close": (17,0)},  # COMEX almost 24 h
    "BTC":    {"tz": "UTC",           "open": (0, 0), "close": (23,59)},
}

def is_market_open(mkt):
    spec = MARKET_HOURS[mkt]
    tz = pytz.timezone(spec["tz"])
    now = dt.now(tz)
    if mkt != "BTC" and now.weekday() >= 5:        # weekend except BTC
        return False
    oh, om = spec["open"];  ch, cm = spec["close"]
    open_t  = tz.localize(dt(now.year, now.month, now.day, oh, om))
    close_t = tz.localize(dt(now.year, now.month, now.day, ch, cm))
    if close_t < open_t:                           # overnight session
        return not (close_t <= now < open_t)
    return open_t <= now < close_t

# --------- Snapshot -------------------------------- #
def snapshot():
    snap = {}
    for name, sym in TICKERS.items():
        tkr = yf.Ticker(sym)
        try:
            fi   = tkr.fast_info
            last = fi["last_price"]
            prev = fi["previous_close"]
        except Exception:
            hist = tkr.history(period="2d", interval="1d")
            if hist.empty: continue
            last, prev = hist["Close"][-1], hist["Close"][-2]
        delta = last - prev
        pct   = delta / prev * 100
        snap[name] = {
            "price":  float(last),
            "delta":  float(delta),
            "pct":    float(pct),
            "closed": not is_market_open(name),
        }
    return snap

def format_snapshot(snap: dict) -> str:
    lines = [f"Snapshot @ {dt.now(pytz.timezone('Asia/Bangkok')):%Y-%m-%d %H:%M:%S}"]
    for k, v in snap.items():
        price = f"{v['price']:>12,.2f}"
        chg   = f"{v['delta']:+,.2f}"
        pct   = f"{v['pct']:+.2f}%"
        tail  = f"({chg} | {pct})"
        if v["closed"]: tail += "  Close"
        lines.append(f"{k:<7}: {price}  {tail}")
    return "\n".join(lines)

# --------- Telegram -------------------------------- #
BOT_TOKEN = os.getenv("TG_TOKEN")   or "7614105366:AAGHR8ZMYO6qD1CqBJGtkMbHB4WY5way9nw"
CHAT_ID   = os.getenv("TG_CHAT_ID") or "5971502597"

def tg_send(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    status = "✅" if r.status_code == 200 else f"⚠️ {r.text}"
    print(status)

# --------- Main loop ------------------------------- #
def run_once():
    msg = format_snapshot(snapshot())
    print(msg)          # log to console
    tg_send(msg)

if __name__ == "__main__":
    #INTERVAL = 3600      # วินาที (1 ชม.) — เปลี่ยนตามต้องการ
    try:
        #while True:
            run_once()
            #time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped by user")
