#!/bin/bash
# Quick GOOGL Price Check
# Run anytime to check if GOOGL dropped 10%

echo "🔔 GOOGL Price Alert Monitor"
echo "============================"
echo "Baseline: \$310.96"
echo "Alert Threshold: \$279.86 (10% drop)"
echo ""

# Fetch current price
PRICE=$(curl -s "https://query1.finance.yahoo.com/v8/finance/chart/GOOGL" | \
  grep -o '"regularMarketPrice":[0-9.]*' | head -1 | cut -d':' -f2)

if [ -z "$PRICE" ]; then
    echo "❌ Could not fetch price"
    exit 1
fi

echo "📈 Current GOOGL Price: \$$PRICE"

# Calculate drop
BASELINE=310.96
DROP=$(echo "scale=2; ($BASELINE - $PRICE) / $BASELINE * 100" | bc)
THRESHOLD=279.86

echo "📉 Drop from baseline: ${DROP}%"

if (( $(echo "$PRICE < $THRESHOLD" | bc -l) )); then
    echo ""
    echo "🚨 ALERT! GOOGL has dropped more than 10%!"
    echo "Current: \$$PRICE"
    echo "Threshold: \$$THRESHOLD"
    echo ""
    echo "Run this to get notified:"
    echo "  osascript -e 'display notification \"GOOGL dropped ${DROP}%!\" with title \"Price Alert\"'"
    osascript -e 'display notification "GOOGL dropped '${DROP}%' to $'${PRICE}'!" with title "🚨 Price Alert"'
else
    echo "✅ Price above threshold (\$$THRESHOLD)"
fi
