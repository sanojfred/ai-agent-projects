import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import fo_agents as fa


class AgentTests(unittest.TestCase):
    def test_sma_and_rsi(self):
        self.assertEqual(fa.sma([1, 2, 3, 4], 2), [None, 1.5, 2.5, 3.5])
        up = fa.rsi([float(i) for i in range(1, 40)])
        self.assertEqual(up[-1], 100.0)

    def test_trend_agent_long_in_uptrend(self):
        candles = [{"date": str(i), "open": i, "high": i + 1, "low": i - 1, "close": i + 100.0} for i in range(120)]
        self.assertEqual(fa.trend_agent(candles)[-1], 1)

    def test_backtest_perfect_long_has_no_losses(self):
        candles = [{"date": str(i), "open": 1, "high": 1, "low": 1, "close": 100 * 1.01 ** i} for i in range(200)]
        m = fa.backtest(candles, [1] * 200, cost_bps=0)
        self.assertAlmostEqual(m["total_return"], 1.01 ** 199 - 1, places=6)
        self.assertEqual(m["max_drawdown"], 0.0)

    def test_costs_reduce_returns(self):
        c = fa.synthetic()
        s = fa.trend_agent(c)
        self.assertLess(fa.backtest(c, s, 50)["total_return"], fa.backtest(c, s, 0)["total_return"])

    def test_analyse_produces_consistent_setup(self):
        res = fa.analyse(fa.synthetic())
        st = res["setup"]
        if st["direction"] == "LONG":
            self.assertTrue(st["stop"] < st["entry"] < st["target"])
        elif st["direction"] == "SHORT":
            self.assertTrue(st["target"] < st["entry"] < st["stop"])
        else:
            self.assertEqual(st["direction"], "NO TRADE")

    def test_csv_roundtrip(self):
        import tempfile, csv
        c = fa.synthetic(150)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close"])
            w.writeheader(); w.writerows(c)
        self.assertEqual(len(fa.load_csv(f.name)), 150)
        os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
