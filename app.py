import streamlit as st
import yfinance as yf
import pandas as pd
import ta

# Page Configuration
st.set_page_config(page_title="Saru Select", layout="wide")
st.title("Saru Select")

# --- 1. Top Live Price Bar ---
col_nifty, col_banknifty = st.columns(2)

@st.cache_data(ttl=60)
def get_index_price(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period="2d")
        if len(data) >= 2:
            latest = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            change = latest - prev
            pct_change = (change / prev) * 100
            return latest, change, pct_change
    except Exception:
        pass
    return None, None, None

nifty_price, nifty_change, nifty_pct = get_index_price("^NSEI")
bank_price, bank_change, bank_pct = get_index_price("^NSEBANK")

with col_nifty:
    if nifty_price:
        st.metric(label="Nifty Live Price", value=f"₹{nifty_price:,.2f}", delta=f"{nifty_change:+.2f} ({nifty_pct:+.2f}%)")
    else:
        st.write("Nifty Live Price: Unavailable")

with col_banknifty:
    if bank_price:
        st.metric(label="Bank Nifty Live Price", value=f"₹{bank_price:,.2f}", delta=f"{bank_change:+.2f} ({bank_pct:+.2f}%)")
    else:
        st.write("Bank Nifty Live Price: Unavailable")

st.markdown("---")

# --- Sidebar Inputs ---
st.sidebar.header("Parameters")

# Timeframe Selection
timeframe_map = {
    "15 min": "15m",
    "1 hour": "60m",
    "4 hour": "1h", # Approximated via resampling
    "1 day": "1d",
    "1 week": "1wk"
}
selected_tf_label = st.sidebar.selectbox("Select Time Frame", list(timeframe_map.keys()), index=3)
selected_tf = timeframe_map[selected_tf_label]

# Stock List Selection
stock_lists = {
    "Nifty 50": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LTIM.NS"],
    "Nifty Next 50": ["BEL.NS", "COALINDIA.NS", "DLF.NS", "HAL.NS", "IOC.NS", "IRFC.NS", "JIOFIN.NS", "PFC.NS", "RECLTD.NS", "SIEMENS.NS"],
    "Nifty 200": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "TATAMOTORS.NS", "AXISBANK.NS", "ADANIENT.NS"],
    "Nifty 500": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "ZOMATO.NS", "PAYTM.NS", "POLICYBZR.NS"],
    "Nifty F&O": ["BANKBARODA.NS", "CANBK.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS", "PNB.NS", "RBLBANK.NS"]
}
selected_list_label = st.sidebar.selectbox("Select Stock List", list(stock_lists.keys()))
selected_stocks = stock_lists[selected_list_label]

# Moving Average Inputs
st.sidebar.subheader("SMA Settings")
sma1_val = st.sidebar.selectbox("Select SMA 1 (Short)", [10, 20, 50, 100, 200], index=0)
sma2_val = st.sidebar.selectbox("Select SMA 2 (Long)", [100, 200, 50], index=0)

# MACD Inputs
st.sidebar.subheader("MACD Settings")
macd_fast = st.sidebar.number_input("Short SMA (Fast)", value=12)
macd_slow = st.sidebar.number_input("Long SMA (Slow)", value=26)
macd_signal = st.sidebar.number_input("Signal SMA", value=9)

# --- Fetch & Analyze Data ---
def fetch_data(ticker, period, interval):
    data = yf.download(ticker, period=period, interval=interval, progress=False)
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

def analyze_stock(ticker):
    if selected_tf in ["15m", "60m", "1h"]:
        period = "1mo"
    else:
        period = "2y"
        
    df = fetch_data(ticker, period=period, interval="60m" if selected_tf == "1h" else selected_tf)
    
    if df.empty or len(df) < max(sma1_val, sma2_val, macd_slow + macd_signal):
        return None

    if selected_tf_label == "4 hour":
        df = df.resample('4h').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

    df['SMA1'] = df['Close'].rolling(window=sma1_val).mean()
    df['SMA2'] = df['Close'].rolling(window=sma2_val).mean()

    macd_obj = ta.trend.MACD(
        close=df['Close'], 
        window_slow=macd_slow, 
        window_fast=macd_fast, 
        window_sign=macd_signal
    )
    df['MACD'] = macd_obj.macd()
    df['MACD_Signal'] = macd_obj.macd_signal()

    df = df.dropna()
    if len(df) < 2:
        return None

    curr = df.iloc[-1]
    prev = df.iloc[-2]

    sma_buy = (prev['SMA1'] <= prev['SMA2']) and (curr['SMA1'] > curr['SMA2'])
    sma_sell = (prev['SMA1'] >= prev['SMA2']) and (curr['SMA1'] < curr['SMA2'])

    macd_buy = (prev['MACD'] <= prev['MACD_Signal']) and (curr['MACD'] > curr['MACD_Signal'])
    macd_sell = (prev['MACD'] >= prev['MACD_Signal']) and (curr['MACD'] < curr['MACD_Signal'])

    return {
        "Ticker": ticker.replace(".NS", ""),
        "Price": f"₹{curr['Close']:.2f}",
        "SMA Buy Signal": "BUY" if sma_buy else "-",
        "SMA Sell Signal": "SELL" if sma_sell else "-",
        "MACD Buy Signal": "BUY" if macd_buy else "-",
        "MACD Sell Signal": "SELL" if macd_sell else "-"
    }

# --- Display Results ---
st.subheader(f"Screening Results ({selected_list_label} - {selected_tf_label})")

if st.button("Run Screener"):
    results = []
    with st.spinner("Analyzing stocks..."):
        for symbol in selected_stocks:
            res = analyze_stock(symbol)
            if res:
                results.append(res)
    
    if results:
        res_df = pd.DataFrame(results)
        st.dataframe(res_df, use_container_width=True)
    else:
        st.info("No data available for the selected criteria.")
else:
    st.info("Click 'Run Screener' to load signals.")
