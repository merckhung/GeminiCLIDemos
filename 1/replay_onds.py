import yfinance as yf
import pandas as pd
import time
import sys
from datetime import datetime

def replay_onds_trading():
    ticker = 'ONDS'
    print(f"Fetching 1-minute data for {ticker}...")
    
    # Fetch 1-minute data
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
    
    # Handle MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        try:
             df.columns = df.columns.droplevel(1)
        except IndexError:
             pass

    # Filter data for only the last trading day
    day_data = df[df.index.date == last_date]
    
    if day_data.empty:
        print("No data available for the last date.")
        return

    print(f"\nStarting Replay for {ticker} on {last_date}")
    print(f"Speed: 1 minute market time = 0.3 second real time")
    print("-" * 80)
    print(f"{ 'Time':<10} | { 'Open':<8} | { 'High':<8} | { 'Low':<8} | { 'Close':<8} | { 'Volume':<8} | { 'Change%':<8}")
    print("-" * 80)

    # Replay loop
    try:
        for index, row in day_data.iterrows():
            # Format time
            current_time = index.strftime('%H:%M')
            
            # Extract values
            open_p = row['Open']
            high_p = row['High']
            low_p = row['Low']
            close_p = row['Close']
            volume = row['Volume']
            
            # Calculate change from open
            change_pct = ((close_p - open_p) / open_p) * 100
            
            # Determine color (simulation using ANSI codes)
            # Green if positive, Red if negative
            color_code = "\033[92m" if change_pct >= 0 else "\033[91m"
            reset_code = "\033[0m"
            
            # Print row
            line = f"{current_time:<10} | {open_p:<8.2f} | {high_p:<8.2f} | {low_p:<8.2f} | {close_p:<8.2f} | {volume:<8.0f} | {color_code}{change_pct:<8.2f}%{reset_code}"
            print(line)
            
            # Flush stdout to ensure immediate printing
            sys.stdout.flush()
            
            # Sleep for 0.3 seconds (mapping 1min to 0.3s)
            time.sleep(0.3)
            
    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")

if __name__ == "__main__":
    replay_onds_trading()
