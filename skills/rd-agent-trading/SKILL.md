# RD-Agent Trading Skill

AI-driven US stock trading signal system based on Microsoft's RD-Agent-Quant architecture.

## Overview

This skill implements a three-stage iterative trading system inspired by the RD-Agent-Quant paper (arXiv:2505.15155):

```
Research → Develop → Feedback
```

## Features

### 1. Research Module
- Integrates multiple data sources:
  - Polymarket for market sentiment
  - WeChat hotspots for trending topics
  - Technical analysis for patterns
  - Position monitoring for risk

### 2. Develop Module
- Generates AI-driven trading signals
- Signal levels:
  - 🟢 Strong Buy (>80)
  - 🟡 Buy (60-80)
  - ⚪ Hold (40-60)
  - 🟠 Sell (20-40)
  - 🔴 Strong Sell (<20)

### 3. Feedback Module
- Performance evaluation
- Strategy optimization
- Factor iteration

## Quick Start

```bash
# Run the trading signal system
python3 skills/rd-agent-trading/scripts/rd_agent_trading.py

# View latest report
cat /tmp/rd_agent_trading_report.md
```

## Configuration

Edit `skills/rd-agent-trading/scripts/rd_agent_trading.py`:

```python
CONFIG = {
    "symbols": [
        "QQQ", "NVDA", "TSLA", "GOOGL", "MSFT",
        "AAPL", "AMD", "META", "AMZN", "PLTR"
    ],
    "weights": {
        "polymarket": 0.25,
        "wechat": 0.20,
        "technical": 0.35,
        "risk": 0.20,
    },
    "risk_controls": {
        "stop_loss": 0.05,
        "take_profit": 0.10,
        "max_drawdown": 0.10,
    }
}
```

## Signal Interpretation

### Signal Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Polymarket | 25% | Market sentiment from prediction markets |
| WeChat | 20% | Hot topics from Chinese sources |
| Technical | 35% | Chart patterns and trends |
| Risk | 20% | Position and portfolio risk |

### Example Output

```
🟢 Strong Buy: PLTR (84.2)
   - Confidence: 84%
   - Reasons:
     * Polymarket sentiment positive
     * AI/ML hotspot trending
     * Technical breakout pattern

🟡 Buy: NVDA (82.3)
   - Confidence: 82%
   - Reasons:
     * Semiconductor sector strength
     * AI demand tailwind
```

## Integration

### With Polymarket Skill
```python
# Get market sentiment
from skills.polymarket.scripts.polymarket import get_sentiment

sentiment = get_sentiment("tech")
# Use in RD-Agent scoring
```

### With Portfolio Monitor
```python
# Get current positions
from skills.rd_agent_trading import get_positions

positions = get_positions()
# Risk assessment based on holdings
```

## Cron Scheduling

### Recommended Schedule

| Time | Task |
|------|------|
| 09:00 | Morning trading signals |
| 15:00 | Afternoon update |
| 21:00 | Evening review |

### Cron Expression
```bash
# Morning signals
0 9 * * 1-5

# Afternoon update
0 15 * * 1-5

# Evening review
0 21 * * 1-5
```

## Files

```
skills/rd-agent-trading/
├── SKILL.md              # This file
├── _meta.json            # Skill metadata
└── scripts/
    └── rd_agent_trading.py    # Main trading system
```

## Requirements

- Python 3.8+
- No external dependencies (uses standard library)

## References

- **RD-Agent Paper**: [arXiv:2505.15155](https://arxiv.org/abs/2505.15155)
- **RD-Agent GitHub**: [microsoft/RD-Agent](https://github.com/microsoft/RD-Agent)
- **QLib**: [microsoft/qlib](https://github.com/microsoft/qlib)

## Limitations

- Currently uses simulated data sources
- Not integrated with real trading API
- Backtesting mode only

## Future Enhancements

- [ ] Connect real Polymarket API
- [ ] Integrate technical analysis data (TA-Lib)
- [ ] Add machine learning models
- [ ] Connect Longbridge API for execution
- [ ] Add backtesting module

## Author

Based on RD-Agent-Quant research by Microsoft Research Asia.
