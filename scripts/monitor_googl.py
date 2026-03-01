#!/usr/bin/env python3
"""Google GOOGL Price Monitor - Alerts when drops 10% from baseline"""

import os
import json
import time
from datetime import datetime

# Configuration
SYMBOL = "GOOGL.US"
BASELINE_PRICE = 310.96  # Current price
DROP_THRESHOLD = 0.10    # 10% drop
ALERT_PRICE = BASELINE_PRICE * (1 - DROP_THRESHOLD)
STATE_FILE = "/tmp/googl_monitor_state.json"

def get_current_price():
    """Fetch current price from Longbridge"""
    try:
        from longport.openapi import QuoteContext, Config
        
        config = Config.from_env()
        ctx = QuoteContext(config)
        
        quotes = ctx.quote([SYMBOL])
        if quotes:
            price = quotes[0].last_done
            return float(price)
    except Exception as e:
        print(f"Error fetching price: {e}")
    return None

def check_price():
    """Check if price dropped below threshold"""
    price = get_current_price()
    if price is None:
        print(f"[{datetime.now()}] Could not fetch price")
        return None
    
    drop_percent = (BASELINE_PRICE - price) / BASELINE_PRICE * 100
    
    state = {
        "last_price": price,
        "last_check": str(datetime.now()),
        "baseline": BASELINE_PRICE,
        "alert_triggered": False
    }
    
    # Load existing state
    try:
        with open(STATE_FILE, 'r') as f:
            state.update(json.load(f))
    except:
        pass
    
    print(f"[{datetime.now()}] {SYMBOL}: ${price:.2f} (drop: {drop_percent:.2f}%)")
    
    if price <= ALERT_PRICE and not state.get("alert_triggered"):
        state["alert_triggered"] = True
        state["alert_price"] = price
        state["alert_time"] = str(datetime.now())
        print(f"\n🚨 ALERT: {SYMBOL} dropped {drop_percent:.2f}% to ${price:.2f}!")
        print(f"Threshold was ${ALERT_PRICE:.2f} (10% drop from ${BASELINE_PRICE})")
    
    # Save state
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    return price

if __name__ == "__main__":
    print(f"Monitoring {SYMBOL} for 10% drop from ${BASELINE_PRICE}")
    print(f"Alert threshold: ${ALERT_PRICE:.2f}")
    print("Press Ctrl+C to stop\n")
    
    check_price()
