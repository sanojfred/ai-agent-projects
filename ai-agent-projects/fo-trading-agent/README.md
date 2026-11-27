# F&O Trading Research Agents

**Analysis only. It places no orders. Not financial advice. Backtests do not predict future results, and F&O trading can lose more than you put in.**

`fo_agents.py` runs three strategy agents over price data, backtests each one, and a super-agent combines them into a trade **setup** (direction, entry, stop, target) or `NO TRADE`.

| Agent | Idea |
|---|---|
| trend | 20/50 moving-average crossover |
| mean_reversion | RSI(14) extremes, exit at 50 |
| breakout | 20-bar high/low breakout |
| backtester | Costs charged on every position change; reports return, Sharpe, max drawdown, trades, win rate |
| super-agent | Weights agents by **training-period** Sharpe only, reports **out-of-sample** results separately, sizes stop/target with ATR |

## Use
```
python fo_agents.py --synthetic            # demo on generated data
python fo_agents.py --csv prices.csv       # columns: date,open,high,low,close
python fo_agents.py --csv prices.csv --json
```
Get free daily data from any source you trust and export it to CSV. The synthetic data is random, so its results mean nothing.

## Tests
`python -m unittest discover -s tests`

## Not done yet
- Options-specific logic (greeks, IV, expiries, lot sizes): the current agents work on the underlying price only
- Live data feeds and message delivery of the setup
- Walk-forward optimisation and position sizing
- Paper-trade for a long period before risking real money
