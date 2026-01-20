import time
import os
from firstrade import account

def load_credentials(filepath="credentials.txt"):
    creds = {}
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        return None
    
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                creds[key.strip()] = value.strip()
    return creds

def main():
    creds = load_credentials()
    if not creds:
        return

    username = creds.get("USERNAME")
    password = creds.get("PASSWORD")
    email = creds.get("EMAIL")

    if not all([username, password, email]):
        print("Error: Missing credentials in credentials.txt")
        return

    print("Logging in...")
    try:
        # Create a session
        ft_ss = account.FTSession(username=username, password=password, email=email)
        need_code = ft_ss.login()
        if need_code:
            code = input("Please enter the pin sent to your email/phone: ")
            ft_ss.login_two(code)
    except Exception as e:
        print(f"Login failed: {e}")
        return

    print("Login successful. Starting monitor...")

    while True:
        try:
            # Get account data
            ft_accounts = account.FTAccountData(ft_ss)
            
            if len(ft_accounts.account_numbers) < 1:
                print("No accounts found.")
                break

            # Loop through all accounts
            for account_num in ft_accounts.account_numbers:
                # Get detailed balances
                balances = ft_accounts.get_account_balances(account_num)
                
                # Try to extract relevant info. The keys depend on API response which might vary.
                # We use get_balance_overview as a helper or access directly if we knew keys.
                # Since we don't know exact keys, let's look at what get_balance_overview does or try standard keys.
                # 'total_value' is usually in the account list item.
                
                total_assets = ft_accounts.account_balances.get(account_num, "N/A")
                
                # For Cash and P/L, we verify 'balances' structure or use 'get_balance_overview'
                # Let's inspect 'balances' content with a helper or guess common keys.
                # Common keys in financial APIs: 'money_market_balance', 'net_account_value', 'total_gain_loss'
                # Let's try to find them in the nested dicts if needed.
                
                # To be safe and show everything relevant, let's try to find "Cash" and "Gain"
                
                cash_balance = "N/A"
                pl_amount = "N/A"
                
                # Recursive search for keys
                def find_key(data, target):
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if target.lower() in k.lower():
                                return v
                            if isinstance(v, (dict, list)):
                                res = find_key(v, target)
                                if res: return res
                    elif isinstance(data, list):
                        for item in data:
                            res = find_key(item, target)
                            if res: return res
                    return None

                # Trying to find commonly named keys
                # Adjust these keys based on actual API response if known
                cash_balance = find_key(balances, "cash_balance") or find_key(balances, "money_market") or "N/A"
                
                # P/L might be calculated or provided.
                # Often "total_gain_loss" or similar.
                pl_amount = find_key(balances, "total_gain_loss") or find_key(balances, "gain_loss") or "N/A"
                
                # Fallback for display if we have specific known structure from library (which we don't fully have in static analysis)
                # But 'total_value' is in ft_accounts.account_balances
                
                print(f"Account: {account_num}")
                print(f"Cash Level: {cash_balance}")
                print(f"Total Assets: {total_assets}")
                print(f"P/L: {pl_amount}")
                
                # Get positions
                print("Positions:")
                positions = ft_accounts.get_positions(account=account_num)
                if positions and "items" in positions:
                    for item in positions["items"]:
                        # Print basic info: Symbol, Quantity, Price (if available), Market Value (if available)
                        sym = item.get('symbol', 'N/A')
                        qty = item.get('quantity', 'N/A')
                        # Depending on the API, price might be 'average_buy_price' or similar, and current price might be separate.
                        # We will just dump a formatted string of what we likely have.
                        print(f"  - {sym}: {qty} shares")
                else:
                    print("  No positions found or error retrieving.")

                print("-" * 30)

            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\nStopping monitor.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5) # Retry after error

if __name__ == "__main__":
    main()
