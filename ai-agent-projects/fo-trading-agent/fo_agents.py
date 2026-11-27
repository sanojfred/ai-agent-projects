"""Multi-agent F&O research tool: strategy agents + backtester + a super-agent that outputs a trade SETUP.

Analysis only: it never places orders. Standard library only.
Not financial advice. Backtests do not predict future results.

    python fo_agents.py --synthetic
    python fo_agents.py --csv prices.csv        # columns: date,open,high,low,close[,volume]
"""
import argparse
import csv
import json
import math
import random
import sys


# ---------- data ----------
def load_csv(path):
    candles = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            r = {k.strip().lower(): v for k, v in row.items()}
            candles.append({
                "date": r["date"], "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
            })
    if len(candles) < 120:
        raise ValueError("need at least 120 candles")
    return candles


def synthetic(n=600, seed=7):
    """Random-walk candles with alternating drift regimes (for demos and tests only)."""
    rnd = random.Random(seed)
    price, out = 100.0, []
    for i in range(n):
        drift = 0.0008 if (i // 150) % 2 == 0 else -0.0006
        o = price
        c = o * (1 + drift + rnd.gauss(0, 0.012))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.004)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, 0.004)))
        out.append({"date": f"d{i:04d}", "open": o, "high": h, "low": l, "close": c})
        price = c
    return out


# ---------- indicators ----------
def sma(values, n):
    out, s = [None] * len(values), 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def rsi(closes, n=14):
    out = [None] * len(closes)
    if len(closes) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0); losses += max(-d, 0)
    ag, al = gains / n, losses / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def atr(candles, n=14):
    trs = []
    for i, c in enumerate(candles):
        pc = candles[i - 1]["close"] if i else c["close"]
        trs.append(max(c["high"] - c["low"], abs(c["high"] - pc), abs(c["low"] - pc)))
    return sma(trs, n)


# ---------- strategy agents: each returns one signal per candle (+1 long, -1 short, 0 flat) ----------
def trend_agent(candles, fast=20, slow=50):
    closes = [c["close"] for c in candles]
    f, s = sma(closes, fast), sma(closes, slow)
    return [0 if f[i] is None or s[i] is None else (1 if f[i] > s[i] else -1) for i in range(len(candles))]


def mean_reversion_agent(candles, n=14, low=30, high=70):
    r = rsi([c["close"] for c in candles], n)
    sig, state = [], 0
    for v in r:
        if v is None:
            sig.append(0); continue
        if v < low:
            state = 1
        elif v > high:
            state = -1
        elif (state == 1 and v >= 50) or (state == -1 and v <= 50):
            state = 0
        sig.append(state)
    return sig


def breakout_agent(candles, lookback=20):
    sig, state = [], 0
    for i, c in enumerate(candles):
        if i < lookback:
            sig.append(0); continue
        window = candles[i - lookback:i]
        if c["close"] > max(x["high"] for x in window):
            state = 1
        elif c["close"] < min(x["low"] for x in window):
            state = -1
        sig.append(state)
    return sig


AGENTS = {"trend": trend_agent, "mean_reversion": mean_reversion_agent, "breakout": breakout_agent}


# ---------- backtest agent ----------
def backtest(candles, signals, cost_bps=5.0, start=1, end=None):
    """Signal at close i is held through bar i+1. Cost is charged on every position change."""
    end = len(candles) if end is None else end
    closes = [c["close"] for c in candles]
    prev = signals[start - 1] if start > 0 else 0
    rets, trades, cur = [], [], None
    for i in range(start, end):
        pos = signals[i - 1]
        r = pos * (closes[i] / closes[i - 1] - 1)
        if pos != prev:
            r -= abs(pos - prev) * cost_bps / 1e4
            if cur is not None:
                trades.append(cur - 1)
                cur = None
            if pos != 0:
                cur = 1.0
        if cur is not None:
            cur *= 1 + r
        rets.append(r)
        prev = pos
    if cur is not None:
        trades.append(cur - 1)
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
    mean = sum(rets) / len(rets) if rets else 0.0
    sd = math.sqrt(sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)) if len(rets) > 1 else 0.0
    return {
        "total_return": eq - 1,
        "sharpe": (mean / sd * math.sqrt(252)) if sd > 0 else 0.0,
        "max_drawdown": mdd,
        "trades": len(trades),
        "win_rate": (sum(1 for t in trades if t > 0) / len(trades)) if trades else 0.0,
    }


# ---------- super agent ----------
def analyse(candles, train_frac=0.7, cost_bps=5.0, atr_mult=1.5, reward_risk=2.0, min_score=0.5):
    split = int(len(candles) * train_frac)
    sigs = {name: fn(candles) for name, fn in AGENTS.items()}
    report, weights = {}, {}
    for name, s in sigs.items():
        train = backtest(candles, s, cost_bps, 1, split)
        test = backtest(candles, s, cost_bps, split, len(candles))
        report[name] = {"train": train, "out_of_sample": test}
        weights[name] = max(train["sharpe"], 0.0)   # weights come from training data only
    total_w = sum(weights.values())
    score = sum(weights[n] * sigs[n][-1] for n in sigs) / total_w if total_w > 0 else 0.0
    a = atr(candles)[-1]
    last = candles[-1]["close"]
    setup = {"direction": "NO TRADE", "score": round(score, 3)}
    if total_w > 0 and abs(score) >= min_score and a:
        d = 1 if score > 0 else -1
        setup.update({
            "direction": "LONG" if d > 0 else "SHORT",
            "entry": round(last, 2),
            "stop": round(last - d * atr_mult * a, 2),
            "target": round(last + d * atr_mult * a * reward_risk, 2),
            "risk_reward": reward_risk,
        })
    return {"setup": setup, "weights": {k: round(v, 3) for k, v in weights.items()}, "agents": report}


def format_report(res):
    lines = ["F&O RESEARCH REPORT (analysis only, not advice)", ""]
    for n, r in res["agents"].items():
        t, o = r["train"], r["out_of_sample"]
        lines.append(f"{n:15} train sharpe {t['sharpe']:+.2f} | out-of-sample return {o['total_return']:+.1%}, "
                     f"sharpe {o['sharpe']:+.2f}, maxDD {o['max_drawdown']:.1%}, trades {o['trades']}")
    lines += ["", "SETUP: " + json.dumps(res["setup"]),
              "Weights (from training data only): " + json.dumps(res["weights"])]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--csv")
    g.add_argument("--synthetic", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    candles = synthetic() if args.synthetic else load_csv(args.csv)
    res = analyse(candles)
    print(json.dumps(res, indent=2) if args.json else format_report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
