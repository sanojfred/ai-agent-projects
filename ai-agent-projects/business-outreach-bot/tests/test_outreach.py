import csv, os, sys, tempfile, unittest
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
import outreach


class OutreachTests(unittest.TestCase):
    def test_filters_and_dedupes(self):
        leads = outreach.without_website(outreach.load_leads(os.path.join(HERE, "..", "sample", "leads.csv")))
        self.assertEqual([l["name"] for l in leads], ["Sunrise Bakery", "Green Leaf Salon"])

    def test_draft_contains_prices_and_optout(self):
        lead = {"name": "Sunrise Bakery", "category": "Bakery", "city": "Exampleville"}
        text = outreach.draft_quote(lead, "Sam")
        self.assertIn("150 USD", text)
        self.assertIn("won't contact you again", text)
        self.assertTrue(text.rstrip().endswith("Sam"))

    def test_run_writes_files_only(self):
        with tempfile.TemporaryDirectory() as d:
            s = outreach.run(os.path.join(HERE, "..", "sample", "leads.csv"), "Sam", d)
            self.assertEqual(len(s), 2)
            self.assertTrue(os.path.exists(os.path.join(d, "sunrise-bakery-exampleville.txt")))
            rows = list(csv.DictReader(open(os.path.join(d, "summary.csv"))))
            self.assertTrue(all(r["status"] == "draft" for r in rows))

    def test_missing_column(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("name,city\nA,B\n")
        with self.assertRaises(ValueError):
            outreach.load_leads(f.name)
        os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
