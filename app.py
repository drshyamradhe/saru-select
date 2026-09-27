import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title='SARU Select — Free Trial', page_icon='📈', layout='wide')

st.markdown('''
<style>
.block-container {padding-top: .8rem; padding-bottom: 1.5rem; max-width: 1200px;}
.stButton button {width:100%;}
.small {font-size:.82rem; opacity:.75;}
</style>
''', unsafe_allow_html=True)

TIMEFRAMES = {
    '15m': {'yf_interval':'15m','period':'60d','resample':None},
    '1H': {'yf_interval':'60m','period':'730d','resample':None},
    '4H': {'yf_interval':'60m','period':'730d','resample':'4h'},
    '1D': {'yf_interval':'1d','period':'10y','resample':None},
    '1W': {'yf_interval':'1d','period':'10y','resample':'W-FRI'},
}

NIFTY50 = [
('ADANIENT','Adani Enterprises'),('ADANIPORTS','Adani Ports'),('APOLLOHOSP','Apollo Hospitals'),
('ASIANPAINT','Asian Paints'),('AXISBANK','Axis Bank'),('BAJAJ-AUTO','Bajaj Auto'),('BAJFINANCE','Bajaj Finance'),
('BAJAJFINSV','Bajaj Finserv'),('BEL','Bharat Electronics'),('BHARTIARTL','Bharti Airtel'),('CIPLA','Cipla'),
('COALINDIA','Coal India'),('DRREDDY','Dr Reddy\'s'),('EICHERMOT','Eicher Motors'),('ETERNAL','Eternal'),
('GRASIM','Grasim Industries'),('HCLTECH','HCL Technologies'),('HDFCBANK','HDFC Bank'),('HDFCLIFE','HDFC Life'),
('HEROMOTOCO','Hero MotoCorp'),('HINDALCO','Hindalco'),('HINDUNILVR','Hindustan Unilever'),('ICICIBANK','ICICI Bank'),
('INDUSINDBK','IndusInd Bank'),('INFY','Infosys'),('ITC','ITC'),('JIOFIN','Jio Financial Services'),('JSWSTEEL','JSW Steel'),
('KOTAKBANK','Kotak Mahindra Bank'),('LT','Larsen & Toubro'),('M&M','Mahindra & Mahindra'),('MARUTI','Maruti Suzuki'),
('MAXHEALTH','Max Healthcare'),('NESTLEIND','Nestle India'),('NTPC','NTPC'),('ONGC','ONGC'),('POWERGRID','Power Grid'),
('RELIANCE','Reliance Industries'),('SBILIFE','SBI Life'),('SBIN','State Bank of India'),('SHRIRAMFIN','Shriram Finance'),
('SUNPHARMA','Sun Pharma'),('TATACONSUM','Tata Consumer'),('TATASTEEL','Tata Steel'),('TCS','TCS'),('TECHM','Tech Mahindra'),
('TITAN','Titan'),('TRENT','Trent'),('ULTRACEMCO','UltraTech Cement'),('WIPRO','Wipro')]

UNIVERSES = {'NIFTY 50': NIFTY50}

def ticker(sym):
    return sym + '.NS'

def normalize(df):
    if df is None or df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={c:c.title() for c in df.columns})
    cols = [c for c in ['Open','High','Low','Close','Volume'] if c in df.columns]
    df = df[cols].dropna(subset=['Close']).copy()
    return df

@st.cache_data(ttl=300, show_spinner=False)
def load_history(sym, tf):
    cfg = TIMEFRAMES[tf]
    try:
        df = yf.download(ticker(sym), period=cfg['period'], interval=cfg['yf_interval'],
                         auto_adjust=False, progress=False, threads=False)
        df = normalize(df)
        if df.empty: return df
        if cfg['resample']:
            rule = cfg['resample']
            agg = {'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}
            df = df.resample(rule).agg(agg).dropna(subset=['Close'])
        # Use completed bars only: conservatively remove the latest bar.
        if len(df) > 2:
            df = df.iloc[:-1]
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def market_quote(symbol):
    try:
        df = yf.download(symbol, period='5d', interval='1d', auto_adjust=False, progress=False, threads=False)
        df = normalize(df)
        if df.empty: return None, None
        last = float(df['Close'].iloc[-1])
        prev = float(df['Close'].iloc[-2]) if len(df) > 1 else last
        pct = (last-prev)/prev*100 if prev else 0
        return last, pct
    except Exception:
        return None, None

def sma_signal(df, s1, s2):
    if len(df) < max(s1,s2)+2: return '—', None
    a=df['Close'].rolling(s1).mean(); b=df['Close'].rolling(s2).mean()
    if pd.isna(a.iloc[-2]) or pd.isna(b.iloc[-2]): return '—', None
    if a.iloc[-2] <= b.iloc[-2] and a.iloc[-1] > b.iloc[-1]: return 'BUY', df.index[-1]
    if a.iloc[-2] >= b.iloc[-2] and a.iloc[-1] < b.iloc[-1]: return 'SELL', df.index[-1]
    return '—', None

def macd_signal(df, fast, slow, signal):
    if len(df) < slow+signal+3: return '—', None, None, None
    m=df['Close'].ewm(span=fast,adjust=False).mean()-df['Close'].ewm(span=slow,adjust=False).mean()
    s=m.ewm(span=signal,adjust=False).mean()
    if m.iloc[-2] <= s.iloc[-2] and m.iloc[-1] > s.iloc[-1]: return 'BUY', df.index[-1], m.iloc[-1], s.iloc[-1]
    if m.iloc[-2] >= s.iloc[-2] and m.iloc[-1] < s.iloc[-1]: return 'SELL', df.index[-1], m.iloc[-1], s.iloc[-1]
    return '—', None, m.iloc[-1], s.iloc[-1]

def scan(symbols, tf, s1, s2, mf, ms, mg):
    rows=[]
    for sym,name in symbols:
        df=load_history(sym,tf)
        if df.empty: continue
        ss,sd=sma_signal(df,s1,s2)
        mm,md,mv,sv=macd_signal(df,mf,ms,mg)
        rows.append({'Symbol':sym,'Name':name,'Price':float(df['Close'].iloc[-1]),
                     'SMA Signal':ss,'SMA Cross':sd,'MACD Signal':mm,'MACD Cross':md,
                     'MACD':mv,'Signal':sv})
    return pd.DataFrame(rows)

def fmt_date(x):
    if pd.isna(x) or x is None: return ''
    try: return pd.Timestamp(x).strftime('%d-%b-%Y')
    except: return ''

def chart(sym, tf, s1, s2, mf, ms, mg):
    df=load_history(sym,tf)
    if df.empty: return None
    c=df['Close']; sma1=c.rolling(s1).mean(); sma2=c.rolling(s2).mean()
    macd=c.ewm(span=mf,adjust=False).mean()-c.ewm(span=ms,adjust=False).mean(); sig=macd.ewm(span=mg,adjust=False).mean()
    fig=go.Figure()
    fig.add_trace(go.Candlestick(x=df.index,open=df.Open,high=df.High,low=df.Low,close=df.Close,name='Price'))
    fig.add_trace(go.Scatter(x=df.index,y=sma1,name=f'SMA {s1}',mode='lines'))
    fig.add_trace(go.Scatter(x=df.index,y=sma2,name=f'SMA {s2}',mode='lines'))
    fig.update_layout(height=480,margin=dict(l=10,r=10,t=35,b=10),xaxis_rangeslider_visible=False)
    return fig, df, macd, sig

st.title('📈 SARU SELECT')
st.caption('FREE TRIAL MODE • No broker account or API credentials required')

# Market header
q1,p1=market_quote('^NSEI'); q2,p2=market_quote('^NSEBANK')
c1,c2,c3=st.columns(3)
c1.metric('NIFTY 50', f'₹{q1:,.2f}' if q1 else 'Unavailable', f'{p1:+.2f}%' if p1 is not None else None)
c2.metric('BANK NIFTY', f'₹{q2:,.2f}' if q2 else 'Unavailable', f'{p2:+.2f}%' if p2 is not None else None)
c3.metric('GIFT NIFTY', 'Not in trial feed', help='GIFT NIFTY is intentionally disabled in this free trial data layer.')

with st.sidebar:
    st.header('SARU Controls')
    tf=st.selectbox('Time frame', list(TIMEFRAMES.keys()), index=3)
    universe=st.selectbox('Stock list', list(UNIVERSES.keys()))
    s1=st.selectbox('SMA 1', [10,20,50,100,200], index=1)
    s2=st.selectbox('SMA 2', [20,50,100,200], index=1)
    st.subheader('MACD')
    mf=st.number_input('Short EMA', min_value=2, max_value=100, value=12)
    ms=st.number_input('Long EMA', min_value=3, max_value=200, value=26)
    mg=st.number_input('Signal EMA', min_value=2, max_value=100, value=9)
    run=st.button('🔍 RUN SCREEN', type='primary')
    st.info('Trial data uses Yahoo Finance via yfinance. It is intended for testing, not execution. Intraday availability/rate limits are controlled by the upstream feed.')

if 'results' not in st.session_state or run:
    if s1 >= s2: st.error('SMA 1 must be smaller than SMA 2 for this crossover setup.')
    else:
        with st.spinner('Scanning…'):
            st.session_state.results=scan(UNIVERSES[universe],tf,s1,s2,mf,ms,mg)
        st.session_state.params=(tf,s1,s2,mf,ms,mg)

res=st.session_state.get('results',pd.DataFrame())
if res.empty:
    st.warning('Tap RUN SCREEN to start. If no rows appear, the free upstream feed may be temporarily unavailable or rate-limited.')
else:
    sma_buy=res[res['SMA Signal']=='BUY'].copy(); sma_sell=res[res['SMA Signal']=='SELL'].copy()
    macd_buy=res[res['MACD Signal']=='BUY'].copy(); macd_sell=res[res['MACD Signal']=='SELL'].copy()
    st.subheader('Signals')
    a,b,c,d=st.columns(4)
    a.metric('🟢 SMA BUY',len(sma_buy)); b.metric('🔴 SMA SELL',len(sma_sell)); c.metric('🟢 MACD BUY',len(macd_buy)); d.metric('🔴 MACD SELL',len(macd_sell))
    tabs=st.tabs(['🟢 SMA BUY','🔴 SMA SELL','🟢 MACD BUY','🔴 MACD SELL','All scanned'])
    def show(df, kind):
        if df.empty: st.info('No fresh crossover detected on the last completed candle.')
        else:
            x=df[['Symbol','Name','Price']].copy()
            x['Cross date']=df['SMA Cross' if kind=='SMA' else 'MACD Cross'].map(fmt_date)
            st.dataframe(x,hide_index=True,use_container_width=True)
    with tabs[0]: show(sma_buy,'SMA')
    with tabs[1]: show(sma_sell,'SMA')
    with tabs[2]: show(macd_buy,'MACD')
    with tabs[3]: show(macd_sell,'MACD')
    with tabs[4]:
        st.dataframe(res[['Symbol','Name','Price','SMA Signal','MACD Signal']],hide_index=True,use_container_width=True)

    st.divider(); st.subheader('📊 Stock chart')
    sym=st.selectbox('Select stock', [x[0] for x in UNIVERSES[universe]])
    out=chart(sym,tf,s1,s2,mf,ms,mg)
    if out:
        fig,df,macd,sig=out
        st.plotly_chart(fig,use_container_width=True)
        ss,sd=sma_signal(df,s1,s2); mm,md,mv,sv=macd_signal(df,mf,ms,mg)
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f'**SMA {s1}/{s2}:** `{ss}`')
            if sd: st.caption('Crossover: '+fmt_date(sd))
        with c2:
            st.markdown(f'**MACD {mf}/{ms}/{mg}:** `{mm}`')
            if md: st.caption('Crossover: '+fmt_date(md))

st.caption('Data-source note: trial mode is for testing the application. Verify market data with an official broker/exchange feed before making trading decisions.')
