# Longbridge Trading Skill

AI-powered trading automation with Longbridge API.

## Quick Start

```bash
# View portfolio
python3 bin/dashboard.py

# Get quote
python3 bin/tools.py quote QQQ.US AAPL.US NVDA.US

# Check balance
python3 bin/tools.py balance

# View orders
python3 bin/tools.py orders
```

## Install

```bash
pip install longbridge
```

## Configure

Create `~/.openclaw/longbridge_tokens.json`:
```json
{
  "app_key": "your_app_id",
  "access_token": "your_oauth_token"
}
```

## More Info

See [SKILL.md](SKILL.md) for full documentation.
