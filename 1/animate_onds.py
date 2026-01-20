import yfinance as yf
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import time

def animate_onds():
    ticker = 'ONDS'
    print(f"Fetching 1-minute data for {ticker}...")
    
    try:
        df = yf.download(ticker, period='5d', interval='1m', progress=False)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    if df.empty:
        print(f"No data found for {ticker}.")
        return

    df.index = pd.to_datetime(df.index)
    last_date = df.index.date[-1]
    
    if isinstance(df.columns, pd.MultiIndex):
        try:
             df.columns = df.columns.droplevel(1)
        except:
             pass

    day_data = df[df.index.date == last_date].copy()
    
    if day_data.empty:
        print("No data available for the last date.")
        return

    # Calculate VWAP
    # Typical Price
    day_data['Typical_Price'] = (day_data['High'] + day_data['Low'] + day_data['Close']) / 3
    # Volume * Price
    day_data['VP'] = day_data['Typical_Price'] * day_data['Volume']
    # Cumulative totals
    day_data['Total_VP'] = day_data['VP'].cumsum()
    day_data['Total_Volume'] = day_data['Volume'].cumsum()
    # VWAP
    day_data['VWAP'] = day_data['Total_VP'] / day_data['Total_Volume']
    
    # Simulation state
    sim_state = {
        'deviation': 0.01, # 1% default
        'position': 0,
        'avg_price': 0.0,
        'cash': 10000.0, # Starting balance
        'current_price': 0.0,
        'realized_pnl': 0.0
    }

    print(f"Starting animated replay for {last_date}...")
    print("Controls: Press '+' to increase deviation, '-' to decrease.")
    print("Use Buy/Sell buttons to trade.")
    
    # Set up the figure and axes once
    try:
        fig = mpf.figure(style='charles', figsize=(12, 8))
    except AttributeError:
        fig = plt.figure(figsize=(12, 8))
        
    ax1 = fig.add_subplot(2, 1, 1)
    ax2 = fig.add_subplot(2, 1, 2, sharex=ax1)
    
    # Adjust layout to make room for buttons
    plt.subplots_adjust(bottom=0.2)

    # Key press handler
    def on_key(event):
        step = 0.0005 # 0.05%
        if event.key == '+' or event.key == '=':
            sim_state['deviation'] += step
        elif event.key == '-' or event.key == '_':
            sim_state['deviation'] = max(0.0, sim_state['deviation'] - step)
        print(f"Deviation adjusted to: {sim_state['deviation']:.2%}")

    fig.canvas.mpl_connect('key_press_event', on_key)

    # Trading Functions
    def execute_buy(qty=1):
        price = sim_state['current_price']
        if price > 0:
            total_cost = (sim_state['position'] * sim_state['avg_price']) + (price * qty)
            sim_state['position'] += qty
            sim_state['avg_price'] = total_cost / sim_state['position']
            sim_state['cash'] -= (price * qty)
            print(f"AUTO BUY {qty} @ {price:.2f}. Pos: {sim_state['position']}")

    def execute_sell(qty=1):
        price = sim_state['current_price']
        if price > 0 and sim_state['position'] > 0:
            qty_to_sell = min(qty, sim_state['position'])
            pnl = (price - sim_state['avg_price']) * qty_to_sell
            sim_state['realized_pnl'] += pnl
            sim_state['cash'] += (price * qty_to_sell)
            sim_state['position'] -= qty_to_sell
            if sim_state['position'] == 0:
                sim_state['avg_price'] = 0.0
            print(f"AUTO SELL {qty_to_sell} @ {price:.2f}. Pos: {sim_state['position']}")

    def on_buy_click(event):
        execute_buy(1)

    def on_sell_click(event):
        execute_sell(1)

    ax_buy = plt.axes([0.7, 0.05, 0.1, 0.075])
    ax_sell = plt.axes([0.81, 0.05, 0.1, 0.075])
    btn_buy = Button(ax_buy, 'Buy', color='lightgreen', hovercolor='0.9')
    btn_buy.on_clicked(on_buy_click)
    btn_sell = Button(ax_sell, 'Sell', color='salmon', hovercolor='0.9')
    btn_sell.on_clicked(on_sell_click)
    
    plt.ion()
    plt.show()

    prev_close = None
    prev_lower = None

    try:
        for i in range(len(day_data)):
            visible_df = day_data.iloc[:i+1]
            current_close = visible_df['Close'].iloc[-1]
            sim_state['current_price'] = current_close
            
            current_vwap = visible_df['VWAP'].iloc[-1]
            dev = sim_state['deviation']
            current_lower = current_vwap * (1 - dev)
            
            # Auto-Trading Logic
            if prev_close is not None and prev_lower is not None:
                if prev_close < prev_lower and current_close > current_lower:
                    execute_buy(1)
                if prev_close > prev_lower and current_close < current_lower:
                    if sim_state['position'] > 0:
                         execute_sell(sim_state['position'])

            prev_close = current_close
            prev_lower = current_lower
            
            unrealized_pnl = (current_close - sim_state['avg_price']) * sim_state['position']
            total_pnl = sim_state['realized_pnl'] + unrealized_pnl
            account_value = sim_state['cash'] + (sim_state['position'] * current_close)
            
            ax1.clear()
            ax2.clear()
            
            # Bands for entire visible series
            upper_band = visible_df['VWAP'] * (1 + dev)
            lower_band = visible_df['VWAP'] * (1 - dev)
            
            ap_vwap = mpf.make_addplot(visible_df['VWAP'], ax=ax1, color='orange', width=1.5)
            ap_upper = mpf.make_addplot(upper_band, ax=ax1, color='blue', linestyle='--', width=1.0)
            ap_lower = mpf.make_addplot(lower_band, ax=ax1, color='blue', linestyle='--', width=1.0)
            
            title_text = (f'{ticker} ({last_date}) | Price: {current_close:.2f}\n' 
                          f'Pos: {sim_state["position"]} | Val: ${account_value:.2f} | PnL: ${total_pnl:.2f}')
            
            mpf.plot(visible_df, 
                     type='candle', 
                     style='charles', 
                     ax=ax1, 
                     volume=ax2,
                     addplot=[ap_vwap, ap_upper, ap_lower],
                     axtitle=title_text,
                     ylabel='Price ($)',
                     ylabel_lower='Volume')
            
            plt.pause(0.3)
            if not plt.fignum_exists(fig.number):
                break
                
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        plt.ioff()
        if plt.fignum_exists(fig.number):
            plt.show()

if __name__ == "__main__":
    animate_onds()
