
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

try:
    from fyers_apiv3 import fyersModel
except Exception:
    fyersModel = None

st.set_page_config(page_title="SARU Select", page_icon="📈", layout="wide")

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1200px;}
h1 {margin-bottom: 0.2rem;}
.small-note {font-size: 0.82rem; opacity: 0.75;}
.signal-buy {background:#e8f7ee; padding:8px 12px; border-radius:10px; font-weight:700;}
.signal-sell {background:#fdecec; padding:8px 12px; border-radius:10px; font-weight:700;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Helpers
# -----------------------------
TIMEFRAMES = {
    "15m": {"resolution": "15", "lookback_days": 60},
    "1H":  {"resolution": "60", "lookback_days": 180},
    "4H":  {"resolution": "240", "lookback_days": 365},
    "1D":  {"resolution": "D", "lookback_days": 900},
    "1W":  {"resolution": "W", "lookback_days": 2500},
}

DEFAULT_UNIVERSES = {
    "NIFTY 50": [
        ("ADANIENT","Adani Enterprises"),("ADANIPORTS","Adani Ports"),("APOLLOHOSP","Apollo Hospitals"),
        ("ASIANPAINT","Asian Paints"),("AXISBANK","Axis Bank"),("BAJAJ-AUTO","Bajaj Auto"),
        ("BAJFINANCE","Bajaj Finance"),("BAJAJFINSV","Bajaj Finserv"),("BEL","Bharat Electronics"),
        ("BHARTIARTL","Bharti Airtel"),("CIPLA","Cipla"),("COALINDIA","Coal India"),("DRREDDY","Dr Reddy's"),
        ("EICHERMOT","Eicher Motors"),("ETERNAL","Eternal"),("GRASIM","Grasim Industries"),
        ("HCLTECH","HCL Technologies"),("HDFCBANK","HDFC Bank"),("HDFCLIFE","HDFC Life"),
        ("HEROMOTOCO","Hero MotoCorp"),("HINDALCO","Hindalco"),("HINDUNILVR","Hindustan Unilever"),
        ("ICICIBANK","ICICI Bank"),("INDUSINDBK","IndusInd Bank"),("INFY","Infosys"),("ITC","ITC"),
        ("JIOFIN","Jio Financial Services"),("JSWSTEEL","JSW Steel"),("KOTAKBANK","Kotak Mahindra Bank"),
        ("LT","Larsen & Toubro"),("M&M","Mahindra & Mahindra"),("MARUTI","Maruti Suzuki"),
        ("MAXHEALTH","Max Healthcare"),("NESTLEIND","Nestle India"),("NTPC","NTPC"),
        ("ONGC","ONGC"),("POWERGRID","Power Grid"),("RELIANCE","Reliance Industries"),
        ("SBILIFE","SBI Life"),("SBIN","State Bank of India"),("SHRIRAMFIN","Shriram Finance"),
        ("SUNPHARMA","Sun Pharma"),("TATACONSUM","Tata Consumer"),("TATASTEEL","Tata Steel"),
        ("TCS","TCS"),("TECHM","Tech Mahindra"),("TITAN","Titan"),("TRENT","Trent"),
        ("ULTRACEMCO","UltraTech Cement"),("WIPRO","Wipro")
    ]
}

# FYERS equity symbol convention
def fyers_symbol(symbol):
    if ":" in symbol:
        return symbol
    return "NSE:" + symbol + "-EQ"

def make_universe_df():
    rows=[]
    for universe, items in DEFAULT_UNIVERSES.items():
        for s,n in items:
            rows.append({"Universe": universe, "Symbol": s, "Name": n})
    return pd.DataFrame(rows)

UNIVERSE_DF = make_universe_df()

def get_client(client_id, access_token):
    if fyersModel is None:
        raise RuntimeError("fyers-apiv3 is not installed.")
    if not client_id or not access_token:
        return None
    return fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")

def history(client, symbol, resolution, start_date, end_date):
    data = {
        "symbol": fyers_symbol(symbol),
        "resolution": resolution,
        "date_format": "1",
        "range_from": start_date.strftime("%Y-%m-%d"),
        "range_to": end_date.strftime("%Y-%m-%d"),
        "cont_flag": "1"
    }
    resp = client.history(data=data)
    if not isinstance(resp, dict) or resp.get("s") != "ok":
        return pd.DataFrame()
    candles = resp.get("candles", [])
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(candles, columns=["timestamp","open","high","low","close","volume"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
    df = df.set_index("datetime")
    return df[["open","high","low","close","volume"]].astype(float).sort_index()

def completed_candles(df, timeframe):
    if df.empty:
        return df
    # FYERS says the candle timestamp marks the beginning of the interval.
    # To avoid using a still-forming candle, drop the latest row.
    return df.iloc[:-1].copy() if len(df) > 2 else df.copy()

def sma(series, period):
    return series.rolling(period).mean()

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def macd_values(close, fast=12, slow=26, signal=9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def cross_up(a, b):
    return len(a) >= 2 and a.iloc[-2] <= b.iloc[-2] and a.iloc[-1] > b.iloc[-1]

def cross_down(a, b):
    return len(a) >= 2 and a.iloc[-2] >= b.iloc[-2] and a.iloc[-1] < b.iloc[-1]

def analyze(df, sma1_period, sma2_period, macd_fast, macd_slow, macd_signal):
    if df.empty:
        return None
    d = df.copy()
    d["sma1"] = sma(d["close"], sma1_period)
    d["sma2"] = sma(d["close"], sma2_period)
    d["macd"], d["macd_signal"], d["macd_hist"] = macd_values(
        d["close"], macd_fast, macd_slow, macd_signal
    )
    needed = max(sma1_period, sma2_period, macd_slow + macd_signal) + 3
    if len(d.dropna()) < needed:
        return None

    last = d.iloc[-1]
    sma_buy = cross_up(d["sma1"], d["sma2"])
    sma_sell = cross_down(d["sma1"], d["sma2"])
    macd_buy = cross_up(d["macd"], d["macd_signal"])
    macd_sell = cross_down(d["macd"], d["macd_signal"])

    signal_date = d.index[-1]
    return {
        "df": d,
        "price": float(last["close"]),
        "sma1": float(last["sma1"]),
        "sma2": float(last["sma2"]),
        "macd": float(last["macd"]),
        "macd_signal": float(last["macd_signal"]),
        "sma_buy": bool(sma_buy),
        "sma_sell": bool(sma_sell),
        "macd_buy": bool(macd_buy),
        "macd_sell": bool(macd_sell),
        "signal_date": signal_date,
    }

def get_quote_prices(client, symbols):
    if not symbols:
        return {}
    out={}
    # FYERS quote API supports up to 50 symbols per request.
    for i in range(0, len(symbols), 50):
        batch = symbols[i:i+50]
        try:
            resp=client.quotes(data={"symbols": ",".join(fyers_symbol(s) for s in batch)})
            if isinstance(resp, dict) and resp.get("s") == "ok":
                for item in resp.get("d", []):
                    v=item.get("v", {})
                    sym=item.get("symbol","")
                    out[sym]=v.get("lp")
        except Exception:
            pass
    return out

def chart_for(df, sma1_period, sma2_period, symbol, timeframe):
    fig=go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="Price"
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["sma1"], name=f"SMA {sma1_period}", mode="lines"))
    fig.add_trace(go.Scatter(x=df.index, y=df["sma2"], name=f"SMA {sma2_period}", mode="lines"))
    fig.update_layout(
        title=f"{symbol} • {timeframe}",
        height=520, xaxis_rangeslider_visible=False,
        margin=dict(l=10,r=10,t=45,b=10)
    )
    return fig

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("⚙️ SARU Settings")
st.sidebar.caption("Mobile-first stock scanner • V1")

client_id = st.sidebar.text_input("FYERS Client ID", type="password")
access_token = st.sidebar.text_input("FYERS Access Token", type="password")

st.sidebar.markdown("---")
timeframe = st.sidebar.selectbox("Time frame", list(TIMEFRAMES.keys()), index=3)

universe_choice = st.sidebar.selectbox(
    "Stock list",
    ["NIFTY 50", "Custom CSV"]
)

uploaded = st.sidebar.file_uploader(
    "Optional: upload universe CSV",
    type=["csv"],
    help="CSV columns: Symbol, Name. Optional Universe column."
)

st.sidebar.markdown("---")
sma1_period = st.sidebar.selectbox("SMA 1", [10,20,50,100,200], index=1)
sma2_options=[20,50,100,200]
sma2_period = st.sidebar.selectbox("SMA 2", sma2_options, index=1)

st.sidebar.markdown("---")
st.sidebar.subheader("MACD")
macd_fast = st.sidebar.number_input("Short EMA", 2, 100, 12)
macd_slow = st.sidebar.number_input("Long EMA", 3, 200, 26)
macd_signal = st.sidebar.number_input("Signal EMA", 2, 100, 9)

max_scan = st.sidebar.slider("Maximum stocks per scan", 10, 500, 50, 10)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Signals use the last completed candle. This avoids treating a still-forming candle as a confirmed crossover."
)

# -----------------------------
# Main header
# -----------------------------
st.title("📈 SARU SELECT")
st.caption("SMA crossover + MACD crossover scanner with individual stock charts")

# Header market data
if client_id and access_token:
    try:
        client=get_client(client_id, access_token)
        header_symbols=["NIFTY50-INDEX","NIFTYBANK-INDEX"]
        prices=get_quote_prices(client, header_symbols)
        c1,c2,c3=st.columns(3)
        with c1:
            st.metric("NIFTY 50", prices.get("NSE:NIFTY50-INDEX","—"))
        with c2:
            st.metric("BANK NIFTY", prices.get("NSE:NIFTYBANK-INDEX","—"))
        with c3:
            st.metric("GIFT NIFTY", "Set symbol")
            st.caption("Use the sidebar/API symbol setting in a later version; do not guess a GIFT quote.")
    except Exception as e:
        st.warning("FYERS connection failed. Check Client ID and Access Token.")
else:
    c1,c2,c3=st.columns(3)
    c1.metric("NIFTY 50","—")
    c2.metric("BANK NIFTY","—")
    c3.metric("GIFT NIFTY","—")
    st.info("Enter your FYERS Client ID and Access Token in the sidebar to load live market data.")

# -----------------------------
# Universe
# -----------------------------
if uploaded is not None:
    try:
        u=pd.read_csv(uploaded)
        required={"Symbol","Name"}
        if not required.issubset(u.columns):
            st.error("CSV must contain Symbol and Name columns.")
            st.stop()
        universe_df=u.copy()
    except Exception:
        st.error("Could not read the uploaded CSV.")
        st.stop()
else:
    universe_df=UNIVERSE_DF[UNIVERSE_DF["Universe"]=="NIFTY 50"].copy()

symbols=universe_df["Symbol"].dropna().astype(str).tolist()
symbols=symbols[:max_scan]

# -----------------------------
# Run scan
# -----------------------------
st.markdown("### 🔍 Scanner")
run=st.button("RUN SCREEN", type="primary", use_container_width=True)

if run:
    if not client_id or not access_token:
        st.error("Enter FYERS Client ID and Access Token first.")
        st.stop()

    client=get_client(client_id, access_token)
    tf=TIMEFRAMES[timeframe]
    end=datetime.now()
    start=end-timedelta(days=tf["lookback_days"])

    results=[]
    progress=st.progress(0)
    status=st.empty()

    for idx,symbol in enumerate(symbols, start=1):
        status.write(f"Scanning {idx}/{len(symbols)}: {symbol}")
        try:
            df=history(client, symbol, tf["resolution"], start, end)
            df=completed_candles(df, timeframe)
            a=analyze(df, sma1_period, sma2_period, macd_fast, macd_slow, macd_signal)
            if a:
                results.append({
                    "Symbol":symbol,
                    "Name":universe_df.loc[universe_df["Symbol"]==symbol,"Name"].iloc[0],
                    "Price":a["price"],
                    "SMA BUY":a["sma_buy"],
                    "SMA SELL":a["sma_sell"],
                    "MACD BUY":a["macd_buy"],
                    "MACD SELL":a["macd_sell"],
                    "Signal Candle":a["signal_date"].strftime("%Y-%m-%d %H:%M"),
                    "_data":a["df"]
                })
        except Exception:
            pass
        progress.progress(idx/len(symbols))

    status.empty()
    progress.empty()

    if not results:
        st.warning("No valid results. Check API credentials, symbols, or try NIFTY 50 with 1D first.")
        st.stop()

    st.session_state["results"]=results
    st.session_state["scan_settings"]={
        "timeframe":timeframe, "sma1":sma1_period, "sma2":sma2_period,
        "macd_fast":macd_fast, "macd_slow":macd_slow, "macd_signal":macd_signal
    }

# -----------------------------
# Results
# -----------------------------
if "results" in st.session_state:
    results=st.session_state["results"]
    settings=st.session_state["scan_settings"]

    rows=[]
    for r in results:
        rows.append({k:v for k,v in r.items() if k!="_data"})
    all_df=pd.DataFrame(rows)

    sma_buy=all_df[all_df["SMA BUY"]].copy()
    sma_sell=all_df[all_df["SMA SELL"]].copy()
    macd_buy=all_df[all_df["MACD BUY"]].copy()
    macd_sell=all_df[all_df["MACD SELL"]].copy()

    st.markdown("### Signals")
    tabs=st.tabs([
        f"🟢 SMA BUY ({len(sma_buy)})",
        f"🔴 SMA SELL ({len(sma_sell)})",
        f"🟢 MACD BUY ({len(macd_buy)})",
        f"🔴 MACD SELL ({len(macd_sell)})",
    ])

    def show_signal(tab, df):
        with tab:
            if df.empty:
                st.info("No crossover detected on the last completed candle.")
            else:
                display=df[["Symbol","Name","Price","Signal Candle"]].copy()
                display["Price"]=display["Price"].round(2)
                st.dataframe(display, use_container_width=True, hide_index=True)

    show_signal(tabs[0],sma_buy)
    show_signal(tabs[1],sma_sell)
    show_signal(tabs[2],macd_buy)
    show_signal(tabs[3],macd_sell)

    st.markdown("### Stock chart")
    selectable=[r["Symbol"] for r in results]
    selected=st.selectbox("Select stock", selectable)

    selected_row=next(r for r in results if r["Symbol"]==selected)
    d=selected_row["_data"]

    st.plotly_chart(
        chart_for(d, settings["sma1"], settings["sma2"], selected, settings["timeframe"]),
        use_container_width=True
    )

    m1,m2,m3,m4=st.columns(4)
    m1.metric("Price", f"₹{selected_row['Price']:.2f}")
    m2.metric(f"SMA {settings['sma1']}", f"₹{selected_row['sma1']:.2f}")
    m3.metric(f"SMA {settings['sma2']}", f"₹{selected_row['sma2']:.2f}")
    m4.metric("MACD", f"{selected_row['macd']:.3f}")

    st.caption(
        f"Last completed candle: {selected_row['Signal Candle']} • "
        f"MACD Signal: {selected_row['macd_signal']:.3f}"
    )

    st.markdown("### Full scan")
    st.dataframe(all_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(
    "SARU is a technical screening tool. A crossover is not a guarantee of future returns. "
    "Verify the signal, liquidity, market conditions and your own risk rules before trading."
)
