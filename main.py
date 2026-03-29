from flask import Flask, jsonify, request, render_template_string
import os
import time
import math
import requests
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

# IMPORTANT:
# Put your key in Render Environment Variables as:
# POLYGON_API_KEY=your_key_here
API_KEY = os.getenv("POLYGON_API_KEY", "")

PAIRS = [
    "C:EURUSD", "C:GBPUSD", "C:USDJPY", "C:AUDUSD",
    "C:USDCAD", "C:USDCHF", "C:NZDUSD", "C:EURJPY",
    "C:GBPJPY", "C:EURGBP", "C:AUDJPY", "C:EURCHF"
]

ACTIVE_SIGNALS = {}
RESULTS = []

HTML = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PUSH</title>
  <style>
    body{margin:0;background:#08111f;color:#eef4ff;font-family:Arial,sans-serif}
    .wrap{max-width:1200px;margin:auto;padding:16px}
    .card{background:#0d1728;border:1px solid #1d2a44;border-radius:18px;padding:16px;margin-bottom:14px;box-shadow:0 10px 25px rgba(0,0,0,.22)}
    .title{font-size:28px;font-weight:700}
    .muted{color:#8fa6cc}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
    .stat{font-size:26px;font-weight:700}
    .controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
    select,button{padding:12px;border-radius:12px;border:1px solid #233555;background:#0a1321;color:#fff}
    button{background:#2563eb;cursor:pointer}
    table{width:100%;border-collapse:collapse}
    th,td{padding:10px 8px;border-bottom:1px solid #192742;text-align:right;font-size:14px}
    .green{color:#22c55e;font-weight:700}
    .red{color:#ef4444;font-weight:700}
    .yellow{color:#f59e0b;font-weight:700}
    .pill{display:inline-block;padding:6px 10px;border-radius:999px;background:#13213a;color:#9cc0ff;font-size:12px}
    .rowcard{background:#0a1321;border:1px solid #1c2a43;border-radius:14px;padding:12px;margin-top:10px}
    .small{font-size:12px;color:#8fa6cc}
    .reason{margin-top:6px;line-height:1.6}
  </style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="title">PUSH</div>
    <div class="muted">Real Market Engine • Global Forex Only</div>
  </div>

  <div class="card">
    <div class="controls">
      <div>
        <div class="small">مدة الصفقة</div>
        <select id="expiry">
          <option value="3">3 دقائق</option>
          <option value="5" selected>5 دقائق</option>
          <option value="10">10 دقائق</option>
        </select>
      </div>
      <div>
        <div class="small">التحديث</div>
        <select id="refresh">
          <option value="20">20 ثانية</option>
          <option value="30" selected>30 ثانية</option>
          <option value="45">45 ثانية</option>
        </select>
      </div>
      <div style="display:flex;align-items:end;gap:8px">
        <button onclick="loadData()">تشغيل المحرك</button>
      </div>
    </div>
    <div id="status" class="small" style="margin-top:10px">جاهز</div>
  </div>

  <div class="grid">
    <div class="card"><div class="small">الاتصال</div><div id="conn" class="stat">—</div></div>
    <div class="card"><div class="small">الإشارات النشطة</div><div id="activeCount" class="stat">0</div></div>
    <div class="card"><div class="small">النتائج</div><div id="resultCount" class="stat">0</div></div>
    <div class="card"><div class="small">أفضل فرصة</div><div id="topPair" class="stat">—</div></div>
  </div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
      <h3 style="margin:0">الماسح المباشر</h3>
      <span id="engine" class="pill">ENGINE</span>
    </div>
    <div style="overflow:auto;margin-top:10px">
      <table>
        <thead>
          <tr>
            <th>الزوج</th>
            <th>السعر</th>
            <th>الإشارة</th>
            <th>الثقة</th>
            <th>الترند</th>
            <th>الهيكل</th>
            <th>السبب</th>
          </tr>
        </thead>
        <tbody id="scannerBody"></tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">الإشارات النشطة</h3>
    <div id="signals"></div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">النتائج بعد الانتهاء</h3>
    <div id="results"></div>
  </div>
</div>

<script>
let timer = null;

function badge(v){
  if(v === "CALL") return '<span class="green">CALL</span>';
  if(v === "PUT") return '<span class="red">PUT</span>';
  if(v === "WIN") return '<span class="green">WIN</span>';
  if(v === "LOSS") return '<span class="red">LOSS</span>';
  return '<span class="yellow">'+v+'</span>';
}

async function loadData(){
  const expiry = document.getElementById("expiry").value;
  document.getElementById("status").innerText = "جارٍ التحديث...";
  try{
    const res = await fetch("/api/scanner?expiry=" + expiry);
    const data = await res.json();
    if(!res.ok) throw new Error(data.error || "Request failed");

    document.getElementById("conn").innerText = data.connected ? "Connected" : "Disconnected";
    document.getElementById("engine").innerText = data.engine;
    document.getElementById("activeCount").innerText = data.active_signals.length;
    document.getElementById("resultCount").innerText = data.results.length;
    document.getElementById("topPair").innerText = data.pairs.length ? data.pairs[0].pair : "—";
    document.getElementById("status").innerText = data.errors.length ? ("أخطاء جزئية: " + data.errors.join(" | ")) : "تم التحديث";

    document.getElementById("scannerBody").innerHTML = data.pairs.map(p => `
      <tr>
        <td>${p.pair}</td>
        <td>${p.price}</td>
        <td>${p.status === "signal" ? badge(p.direction) : badge("NO TRADE")}</td>
        <td>${p.confidence}%</td>
        <td>${p.trend}</td>
        <td>${p.structure}</td>
        <td>${p.reason}</td>
      </tr>
    `).join("");

    document.getElementById("signals").innerHTML = data.active_signals.length ? data.active_signals.map(s => `
      <div class="rowcard">
        <div><b>${s.pair}</b> — ${badge(s.direction)} — ${s.confidence}%</div>
        <div class="small">دخول: ${s.entry_price} | انتهاء: ${s.expiry_minutes} دقائق</div>
        <div class="reason small">${s.reason}</div>
      </div>
    `).join("") : '<div class="small">لا توجد إشارات نشطة الآن</div>';

    document.getElementById("results").innerHTML = data.results.length ? data.results.map(r => `
      <div class="rowcard">
        <div><b>${r.pair}</b> — ${badge(r.direction)} — ${badge(r.result)}</div>
        <div class="small">دخول: ${r.entry_price} | خروج: ${r.exit_price ?? "-"}</div>
      </div>
    `).join("") : '<div class="small">لا توجد نتائج بعد</div>';
  }catch(e){
    document.getElementById("conn").innerText = "Error";
    document.getElementById("engine").innerText = "ERROR";
    document.getElementById("status").innerText = "خطأ: " + e.message;
  }
}

function restartAuto(){
  if(timer) clearInterval(timer);
  const sec = parseInt(document.getElementById("refresh").value, 10);
  timer = setInterval(loadData, sec * 1000);
}

document.getElementById("refresh").addEventListener("change", restartAuto);
loadData();
restartAuto();
</script>
</body>
</html>
"""

def pair_label(symbol: str) -> str:
    return symbol.replace("C:", "")

def get_dates():
    to_date = datetime.now(timezone.utc).date()
    from_date = to_date - timedelta(days=2)
    return from_date.isoformat(), to_date.isoformat()

def fetch_candles(symbol: str):
    if not API_KEY:
        raise RuntimeError("POLYGON_API_KEY missing")

    from_date, to_date = get_dates()
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/"
        f"{from_date}/{to_date}?adjusted=true&sort=asc&limit=300&apiKey={API_KEY}"
    )
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    rows = data.get("results", [])
    if not rows:
        raise RuntimeError("No data")
    return rows

def closes_from_rows(rows):
    return [float(x["c"]) for x in rows]

def highs_from_rows(rows):
    return [float(x["h"]) for x in rows]

def lows_from_rows(rows):
    return [float(x["l"]) for x in rows]

def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val

def rsi(values, period=14):
    if len(values) <= period:
        return None
    gains = []
    losses = []
    for i in range(1, len(values)):
        d = values[i] - values[i - 1]
        gains.append(max(d, 0))
        losses.append(abs(min(d, 0)))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd_hist(values):
    e12 = ema(values, 12)
    e26 = ema(values, 26)
    if e12 is None or e26 is None:
        return None
    return e12 - e26

def support_resistance(rows, lookback=40):
    recent = rows[-lookback:]
    support = min(float(x["l"]) for x in recent)
    resistance = max(float(x["h"]) for x in recent)
    return support, resistance

def structure_state(rows):
    if len(rows) < 10:
        return "Mixed"
    last10 = rows[-10:]
    highs = [float(x["h"]) for x in last10]
    lows = [float(x["l"]) for x in last10]
    if highs[-1] > max(highs[:-1]) and lows[-1] > min(lows[:-1]):
        return "Bullish BOS"
    if lows[-1] < min(lows[:-1]) and highs[-1] < max(highs[:-1]):
        return "Bearish BOS"
    if highs[-1] > highs[-3] and lows[-1] > lows[-3]:
        return "Uptrend"
    if highs[-1] < highs[-3] and lows[-1] < lows[-3]:
        return "Downtrend"
    return "Range"

def analyze_pair(symbol):
    rows = fetch_candles(symbol)
    closes = closes_from_rows(rows)
    highs = highs_from_rows(rows)
    lows = lows_from_rows(rows)

    price = closes[-1]
    open_price = float(rows[-1]["o"])
    ema20 = ema(closes[-60:], 20)
    ema50 = ema(closes[-100:], 50)
    rsi_val = rsi(closes[-50:], 14)
    macd_val = macd_hist(closes[-60:])
    support, resistance = support_resistance(rows)
    structure = structure_state(rows)

    score_call = 0
    score_put = 0
    reasons = []

    if ema20 and ema50:
        if ema20 > ema50:
            score_call += 20
            reasons.append("Bullish EMA alignment")
        elif ema20 < ema50:
            score_put += 20
            reasons.append("Bearish EMA alignment")

    if rsi_val is not None:
        if 45 <= rsi_val <= 65:
            score_call += 10
            reasons.append("RSI supports continuation")
        if 35 <= rsi_val <= 55:
            score_put += 10
            reasons.append("RSI supports pressure")

    if macd_val is not None:
        if macd_val > 0:
            score_call += 12
            reasons.append("Positive momentum")
        elif macd_val < 0:
            score_put += 12
            reasons.append("Negative momentum")

    near_support = abs(price - support) <= max(price * 0.0008, 0.0003)
    near_resistance = abs(price - resistance) <= max(price * 0.0008, 0.0003)

    if near_support and price > open_price:
        score_call += 16
        reasons.append("Support bounce")
    if near_resistance and price < open_price:
        score_put += 16
        reasons.append("Resistance rejection")

    if structure in ("Bullish BOS", "Uptrend"):
        score_call += 14
        reasons.append(structure)
    elif structure in ("Bearish BOS", "Downtrend"):
        score_put += 14
        reasons.append(structure)

    body = abs(price - open_price)
    spread = max(highs[-1] - lows[-1], 1e-9)
    body_ratio = body / spread
    if body_ratio > 0.55:
        if price > open_price:
            score_call += 10
            reasons.append("Strong bullish candle")
        else:
            score_put += 10
            reasons.append("Strong bearish candle")

    direction = "CALL" if score_call >= score_put else "PUT"
    confidence = min(max(score_call, score_put), 95)
    status = "signal" if confidence >= 58 else "no_trade"

    return {
        "symbol": symbol,
        "pair": pair_label(symbol),
        "price": round(price, 5),
        "direction": direction,
        "confidence": int(confidence),
        "status": status,
        "trend": "UP" if (ema20 and ema50 and ema20 > ema50) else "DOWN",
        "structure": structure,
        "reason": ", ".join(reasons[:5]) if reasons else "No clear edge",
    }

def maybe_create_signal(scan, expiry_minutes):
    if scan["status"] != "signal":
        return
    pair = scan["pair"]
    now = int(time.time())
    if pair in ACTIVE_SIGNALS and now < ACTIVE_SIGNALS[pair]["expiry_ts"]:
        return

    ACTIVE_SIGNALS[pair] = {
        "pair": pair,
        "symbol": scan["symbol"],
        "direction": scan["direction"],
        "confidence": scan["confidence"],
        "reason": scan["reason"],
        "entry_price": scan["price"],
        "created_ts": now,
        "expiry_ts": now + expiry_minutes * 60,
        "expiry_minutes": expiry_minutes,
        "result": "PENDING"
    }

def update_results():
    now = int(time.time())
    to_close = []
    for pair, sig in ACTIVE_SIGNALS.items():
        if now >= sig["expiry_ts"]:
            try:
                latest = analyze_pair(sig["symbol"])
                exit_price = latest["price"]
                if sig["direction"] == "CALL":
                    result = "WIN" if exit_price > sig["entry_price"] else "LOSS" if exit_price < sig["entry_price"] else "NEUTRAL"
                else:
                    result = "WIN" if exit_price < sig["entry_price"] else "LOSS" if exit_price > sig["entry_price"] else "NEUTRAL"

                sig["exit_price"] = exit_price
                sig["result"] = result
                RESULTS.insert(0, sig.copy())
                RESULTS[:] = RESULTS[:50]
                to_close.append(pair)
            except Exception:
                pass
    for pair in to_close:
        ACTIVE_SIGNALS.pop(pair, None)

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "configured": bool(API_KEY),
        "active": len(ACTIVE_SIGNALS),
        "results": len(RESULTS)
    })

@app.route("/api/scanner")
def scanner():
    if not API_KEY:
        return jsonify({"error": "POLYGON_API_KEY missing"}), 400

    expiry = int(request.args.get("expiry", 5))
    update_results()

    pairs = []
    errors = []
    for symbol in PAIRS:
        try:
            scan = analyze_pair(symbol)
            pairs.append(scan)
            maybe_create_signal(scan, expiry)
        except Exception as e:
            errors.append(f"{pair_label(symbol)}: {str(e)}")

    pairs.sort(key=lambda x: x["confidence"], reverse=True)

    return jsonify({
        "engine": "PUSH REAL ENGINE",
        "connected": True,
        "pairs": pairs,
        "active_signals": list(ACTIVE_SIGNALS.values()),
        "results": RESULTS,
        "errors": errors[:5]
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
