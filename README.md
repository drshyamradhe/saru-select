# SARU SELECT V1-B — FREE TRIAL MODE

Mobile-first Streamlit stock screener for testing SMA and MACD crossover screening without a broker account or API credentials.

## Trial data source
Uses Yahoo Finance through `yfinance`. No FYERS credentials are required.

## Signals
- SMA BUY: SMA 1 crosses SMA 2 from below.
- SMA SELL: SMA 1 crosses SMA 2 from above.
- MACD BUY: MACD line crosses Signal line from below.
- MACD SELL: MACD line crosses Signal line from above.

Signals use the last completed candle (the newest bar is conservatively excluded).

## Timeframes
15m, 1H, 4H, 1D, 1W. 4H is constructed by resampling 1H data. Free upstream intraday availability and rate limits can change.

## Market header
NIFTY 50 and BANK NIFTY use Yahoo Finance index symbols. GIFT NIFTY is intentionally not shown in trial mode because a stable, authenticated feed should be used for that instrument.

## Run
```bash
streamlit run app.py
```

For mobile-only deployment, upload these files to GitHub and deploy `app.py` with Streamlit Community Cloud.

## Important
This is a technical-screening/testing tool, not an order-execution system. Verify data with an official broker/exchange feed before trading.
