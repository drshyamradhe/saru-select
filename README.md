
# SARU SELECT V1 — Scanner + Charts

Mobile-first Streamlit app for:
- SMA BUY crossover: SMA1 crosses SMA2 from below
- SMA SELL crossover: SMA1 crosses SMA2 from above
- MACD BUY crossover: MACD crosses signal from below
- MACD SELL crossover: MACD crosses signal from above
- 15m / 1H / 4H / 1D / 1W
- NIFTY 50 starter universe
- CSV upload for other universes
- Individual stock candlestick + SMA chart
- Uses last completed candle for signals

## Important
This version uses FYERS API for market data. FYERS currently states that Historical Data, Quotes and Market Data are available to its clients at zero fees.

You need:
- a FYERS account
- FYERS API Client ID
- FYERS API access token

Do NOT put your secret key in this repository.
Do NOT commit access tokens to GitHub.

## Mobile-only deployment
Use GitHub + GitHub Codespaces + Streamlit Community Cloud.

1. Create a GitHub account.
2. Create a repository, e.g. `saru-select`.
3. Upload `app.py` and `requirements.txt`.
4. In Streamlit Community Cloud, connect GitHub and deploy `app.py`.
5. Open the deployed URL on your Android phone.

For editing without a PC, use GitHub Codespaces from the browser.

## Universe CSV
CSV format:

Symbol,Name
INFY,Infosys
TCS,TCS
RELIANCE,Reliance Industries

For FYERS, the app automatically converts `INFY` to `NSE:INFY-EQ`.

## V1 limitations
- NIFTY 50 is included as a starter list.
- Other universes should be supplied with a CSV until a reliable automatic constituent-update layer is added.
- GIFT NIFTY symbol is intentionally not guessed; it will be added after confirming the exact FYERS symbol from the current symbol master.
- This is a scanner, not an auto-trading system.
