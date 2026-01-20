import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
from matplotlib.widgets import Button
import pandas as pd
import numpy as np

# --- Configuration ---
TICKER = "ONDS"
INITIAL_CASH = 10000.0
TRADE_QTY = 1  # Shares per Buy/Sell click
SPEED_INTERVAL = 300  # ms (0.3s)

# --- Data Fetching ---
print(f"Fetching data for {TICKER}...")
try:
    data = yf.Ticker(TICKER).history(period="5d", interval="1m")
    if data.empty:
        raise ValueError("No data returned")
    
    last_day = data.index[-1].date()
    day_data = data[data.index.date == last_day].copy()
    
    if day_data.empty:
        raise ValueError("No data for last trading day")
    
    # Reset index to get integer indexing for simpler plotting
    day_data.reset_index(inplace=True)
    
    print(f"Simulating {last_day} with {len(day_data)} minutes of data.")
    
except Exception as e:
    print(f"Error: {e}")
    exit()

# --- Simulator Class ---
class TradingSimulator:
    def __init__(self, data):
        # Calculate VWAP
        # VWAP = Cumulative(Price * Volume) / Cumulative(Volume)
        # Using Typical Price (High + Low + Close) / 3
        data['Typical_Price'] = (data['High'] + data['Low'] + data['Close']) / 3
        data['VP'] = data['Typical_Price'] * data['Volume']
        data['Cum_VP'] = data['VP'].cumsum()
        data['Cum_Vol'] = data['Volume'].cumsum()
        data['VWAP'] = data['Cum_VP'] / data['Cum_Vol']
        
        self.data = data
        self.current_idx = 0
        self.cash = INITIAL_CASH
        self.position = 0  # Number of shares
        self.equity = INITIAL_CASH
        self.pl = 0.0
        self.current_price = 0.0
        
        # VWAP Deviation
        self.deviation = 0.01  # 1.00%
        
        # Setup Figure and Axes
        self.fig, self.ax_chart = plt.subplots(figsize=(12, 8))
        self.fig.subplots_adjust(bottom=0.25) # More room for 2 sets of buttons
        self.ax_chart.set_position([0.1, 0.30, 0.8, 0.60]) # Adjust chart position

        # Text Info
        self.info_text = self.fig.text(0.1, 0.92, "", fontsize=12, fontweight='bold', 
                                       bbox=dict(facecolor='white', alpha=0.8))
        
        # Buttons (Buy, Sell, Close)
        ax_buy = plt.axes([0.05, 0.1, 0.15, 0.07])
        ax_sell = plt.axes([0.22, 0.1, 0.15, 0.07])
        ax_close = plt.axes([0.39, 0.1, 0.15, 0.07])
        
        self.btn_buy = Button(ax_buy, 'Buy 1', color='lightgreen', hovercolor='green')
        self.btn_sell = Button(ax_sell, 'Sell 1', color='lightcoral', hovercolor='red')
        self.btn_close = Button(ax_close, 'Close Position', color='lightgray', hovercolor='gray')
        
        self.btn_buy.on_clicked(self.buy)
        self.btn_sell.on_clicked(self.sell)
        self.btn_close.on_clicked(self.close_position)
        
        # VWAP Deviation Buttons
        ax_dev_minus = plt.axes([0.65, 0.1, 0.05, 0.07])
        ax_dev_plus = plt.axes([0.85, 0.1, 0.05, 0.07])
        
        self.btn_dev_minus = Button(ax_dev_minus, '-', color='lightblue', hovercolor='blue')
        self.btn_dev_plus = Button(ax_dev_plus, '+', color='lightblue', hovercolor='blue')
        
        self.btn_dev_minus.on_clicked(self.decrease_dev)
        self.btn_dev_plus.on_clicked(self.increase_dev)
        
        # VWAP Deviation Label
        self.dev_text = self.fig.text(0.775, 0.13, f"VWAP Dev\n{self.deviation*100:.2f}%", 
                                      ha='center', va='center', fontsize=9, fontweight='bold')
        
        # Auto Trade Toggle
        self.auto_trade_enabled = True
        ax_auto = plt.axes([0.80, 0.92, 0.1, 0.05])
        self.btn_auto = Button(ax_auto, 'Auto: ON', color='lightgreen', hovercolor='green')
        self.btn_auto.on_clicked(self.toggle_auto_trade)

    def toggle_auto_trade(self, event):
        self.auto_trade_enabled = not self.auto_trade_enabled
        if self.auto_trade_enabled:
            self.btn_auto.label.set_text("Auto: ON")
            self.btn_auto.color = 'lightgreen'
            self.btn_auto.hovercolor = 'green'
        else:
            self.btn_auto.label.set_text("Auto: OFF")
            self.btn_auto.color = 'lightgray'
            self.btn_auto.hovercolor = 'gray'

    def check_auto_trade(self, subset, upper_band_val, lower_band_val):
        if not self.auto_trade_enabled or len(subset) < 5:
            return

        current_vwap = subset['VWAP'].iloc[-1]
        past_vwap = subset['VWAP'].iloc[-4] # Compare vs 3 mins ago
        
        is_uptrend = current_vwap > past_vwap
        
        current_low = subset['Low'].iloc[-1]
        current_high = subset['High'].iloc[-1]
        
        # Rule 1: Uptrend + Touch Lower Band -> Buy 1
        if is_uptrend and current_low <= lower_band_val:
            print(f"[Auto] Uptrend Dip Buy! VWAP Rising.")
            self.buy(None)
            
        # Rule 2: Downtrend + Touch Lower Band -> Sell All (Stop Loss / Bail)
        elif not is_uptrend and current_low <= lower_band_val:
             if self.position > 0:
                print(f"[Auto] Downtrend Breakdown! Selling All.")
                self.close_position(None)

        # Rule 3: Touch Upper Band + Profit -> Sell All (Take Profit)
        if self.position > 0 and current_high >= upper_band_val:
            # Check if profitable
            potential_value = self.position * self.current_price
            # Roughly estimate cost basis (simple approach: current equity - cash)
            # Or just check if current PL is positive
            if self.pl > 0:
                 print(f"[Auto] Upper Band Hit with Profit! Selling All.")
                 self.close_position(None)

    def increase_dev(self, event):
        self.deviation += 0.0005
        self.update_dev_label()

    def decrease_dev(self, event):
        self.deviation = max(0.0, self.deviation - 0.0005)
        self.update_dev_label()

    def update_dev_label(self):
        self.dev_text.set_text(f"VWAP Dev\n{self.deviation*100:.2f}%")

    def update_metrics(self):
        self.equity = self.cash + (self.position * self.current_price)
        self.pl = self.equity - INITIAL_CASH
        
        info = (
            f"Cash: ${self.cash:,.2f}  |  "
            f"Position: {self.position} shares  |  "
            f"Price: ${self.current_price:.2f}\n"
            f"Total Equity: ${self.equity:,.2f}  |  "
            f"P/L: ${self.pl:,.2f}"
        )
        self.info_text.set_text(info)

    def buy(self, event):
        cost = self.current_price * TRADE_QTY
        self.cash -= cost
        self.position += TRADE_QTY
        print(f"BOUGHT {TRADE_QTY} @ {self.current_price:.2f}")
        self.update_metrics()

    def sell(self, event):
        gain = self.current_price * TRADE_QTY
        self.cash += gain
        self.position -= TRADE_QTY
        print(f"SOLD {TRADE_QTY} @ {self.current_price:.2f}")
        self.update_metrics()

    def close_position(self, event):
        if self.position == 0:
            return
        
        value = self.position * self.current_price
        self.cash += value
        print(f"CLOSED {self.position} @ {self.current_price:.2f}")
        self.position = 0
        self.update_metrics()

    def animate(self, i):
        self.current_idx = i + 1
        subset = self.data.iloc[:self.current_idx]
        
        if subset.empty:
            return

        # Update current price
        self.current_price = subset['Close'].iloc[-1]
        self.update_metrics()

        self.ax_chart.clear()
        
        # Draw Candlesticks Manually
        # Width of a candle: 0.6
        width = 0.6
        up_color = 'green'
        down_color = 'red'
        
        up = subset[subset['Close'] >= subset['Open']]
        down = subset[subset['Close'] < subset['Open']]
        
        # Plot Up candles
        if not up.empty:
            self.ax_chart.bar(up.index, up['Close'] - up['Open'], width, bottom=up['Open'], color=up_color)
            self.ax_chart.vlines(up.index, up['Low'], up['High'], color=up_color, linewidth=1)
            
        # Plot Down candles
        if not down.empty:
            self.ax_chart.bar(down.index, down['Close'] - down['Open'], width, bottom=down['Open'], color=down_color)
            self.ax_chart.vlines(down.index, down['Low'], down['High'], color=down_color, linewidth=1)

        # Plot VWAP and Bands
        self.ax_chart.plot(subset.index, subset['VWAP'], color='orange', label='VWAP', linewidth=1.5)
        
        upper_band = subset['VWAP'] * (1 + self.deviation)
        lower_band = subset['VWAP'] * (1 - self.deviation)
        
        self.ax_chart.plot(subset.index, upper_band, color='blue', linestyle='--', linewidth=0.8, label='Upper Band')
        self.ax_chart.plot(subset.index, lower_band, color='blue', linestyle='--', linewidth=0.8, label='Lower Band')
        
        # Auto Trade Logic
        self.check_auto_trade(subset, upper_band.iloc[-1], lower_band.iloc[-1])

        # Dynamic Title & Labels
        # We need to format x-axis to show Time strings, not integers
        # We'll just set ticks for every 15 mins or so to avoid clutter
        
        current_time_str = subset['Datetime'].iloc[-1].strftime('%H:%M')
        self.ax_chart.set_title(f"{TICKER} Simulation - {current_time_str}")
        self.ax_chart.set_ylabel("Price (USD)")
        
        # Grid
        self.ax_chart.grid(True, linestyle=':', alpha=0.6)
        self.ax_chart.legend(loc='upper left')

    def run(self):
        ani = animation.FuncAnimation(self.fig, self.animate, frames=len(self.data), 
                                      interval=SPEED_INTERVAL, repeat=False)
        plt.show()

# --- Run ---
sim = TradingSimulator(day_data)
sim.run()