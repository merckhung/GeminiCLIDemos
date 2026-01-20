import yfinance as yf
import mplfinance as mpf
import pandas as pd

def fetch_and_plot_onds():
    ticker = 'ONDS'
    print(f"Fetching 1-minute data for {ticker}...")
    
    # Fetch 1-minute data for the last 5 days to ensure we capture the most recent trading day
    # yfinance 1m interval is valid for up to 7 days
    try:
        df = yf.download(ticker, period='5d', interval='1m', progress=False)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    if df.empty:
        print(f"No data found for {ticker}.")
        return

    # Ensure the index is a DatetimeIndex
    df.index = pd.to_datetime(df.index)
    
    # Identify the last trading date available in the dataset
    last_date = df.index.date[-1]
    print(f"Displaying data for last trading day: {last_date}")

    # Handle MultiIndex columns (e.g. ('Close', 'ONDS'))
    if isinstance(df.columns, pd.MultiIndex):
        # Drop the Ticker level to get simple 'Open', 'High', etc.
        # Check which level is the ticker (usually level 1)
        # Or just get the level that isn't the price type
        try:
             df.columns = df.columns.droplevel(1)
        except IndexError:
             pass

    # Filter data for only the last trading day
    # We convert the index to date to compare
    day_data = df[df.index.date == last_date]
    
    if day_data.empty:
        print("No data available for the last date.")
        return

    # Plot candlestick chart
    # style='charles' gives a standard green/red candle look
    mpf.plot(day_data, 
             type='candle', 
             style='charles', 
             title=f'{ticker} 1-min K-line ({last_date})',
             ylabel='Price ($)',
             volume=True,
             ylabel_lower='Volume')

if __name__ == "__main__":
    fetch_and_plot_onds()
