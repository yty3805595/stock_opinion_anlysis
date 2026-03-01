#!/bin/bash
# Longbridge OpenAPI Setup Script
# Usage: ./setup.sh

set -e

echo "🚀 Longbridge OpenAPI Setup"
echo "============================"

# Check if credentials are set
if [ -z "$LONGPORT_APP_KEY" ]; then
    echo ""
    echo "📝 To get your credentials:"
    echo "1. Download Longbridge App: https://longbridge.com/download"
    echo "2. Complete account opening"
    echo "3. Visit https://open.longbridge.com and log in"
    echo "4. Go to Developer Center → Personal Center"
    echo ""
fi

# Set environment variables
read -p "Enter LONGPORT_APP_KEY: " APP_KEY
read -p "Enter LONGPORT_APP_SECRET: " APP_SECRET
read -p "Enter LONGPORT_ACCESS_TOKEN: " ACCESS_TOKEN
read -p "Enter LONGPORT_REGION (hk/cn): " REGION

export LONGPORT_APP_KEY="$APP_KEY"
export LONGPORT_APP_SECRET="$APP_SECRET"
export LONGPORT_ACCESS_TOKEN="$ACCESS_TOKEN"
export LONGPORT_REGION="$REGION"

# Install SDK
echo ""
echo "📦 Installing Longbridge SDK..."
pip3 install longport

# Create example files
echo ""
echo "📝 Creating example files..."

cat > get_quote.py << 'EOF'
#!/usr/bin/env python3
"""Get real-time market quotes"""
from longport.openapi import QuoteContext, Config

config = Config.from_env()
ctx = QuoteContext(config)

symbols = ["700.HK", "AAPL.US", "TSLA.US"]
quotes = ctx.quote(symbols)

for symbol, quote in zip(symbols, quotes):
    print(f"{symbol}:")
    print(f"  Last Price: {quote.last_done}")
    print(f"  Open: {quote.open}")
    print(f"  High: {quote.high}")
    print(f"  Low: {quote.low}")
    print(f"  Volume: {quote.volume}")
    print(f"  Turnover: {quote.turnover}")
EOF

cat > submit_order.py << 'EOF'
#!/usr/bin/env python3
"""Submit a test order"""
from decimal import Decimal
from longport.openapi import TradeContext, Config, OrderSide, OrderType, TimeInForceType

config = Config.from_env()
ctx = TradeContext(config)

# Example: Buy 100 shares of 700.HK at 50 HKD
order = ctx.submit_order(
    side=OrderSide.Buy,
    symbol="700.HK",
    order_type=OrderType.LO,
    submitted_price=Decimal("50"),
    submitted_quantity=Decimal("100"),
    time_in_force=TimeInForceType.Day,
    remark="Test order via API",
)

print(f"Order submitted successfully!")
print(f"Order ID: {order.order_id}")
EOF

cat > subscribe_quotes.py << 'EOF'
#!/usr/bin/env python3
"""Subscribe to real-time quotes"""
import time
from longport.openapi import QuoteContext, Config, SubType

config = Config.from_env()
ctx = QuoteContext(config)

def on_quote(symbol, quote):
    print(f"[{symbol}] {quote.last_done} ({quote.timestamp})")

ctx.set_on_quote(on_quote)

symbols = ["700.HK", "AAPL.US"]
ctx.subscribe(symbols, [SubType.Quote], True)

print(f"Subscribed to: {', '.join(symbols)}")
print("Press Ctrl+C to stop...")

try:
    time.sleep(60)
except KeyboardInterrupt:
    print("\nStopped.")
EOF

chmod +x get_quote.py submit_order.py subscribe_quotes.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📁 Example files created:"
echo "   - get_quote.py    : Get real-time quotes"
echo "   - submit_order.py : Submit a test order"
echo "   - subscribe_quotes.py : Subscribe to real-time quotes"
echo ""
echo "🚀 Try it out:"
echo "   python get_quote.py"
echo "   python submit_order.py"
echo ""
