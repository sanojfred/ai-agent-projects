"""Lead filter + quote drafter for a web-design service.

Reads a CSV of local businesses, keeps those WITHOUT a website, and writes one draft
quote per lead plus a summary CSV. It never sends anything: review and send drafts yourself.
Optional --use-llm polishes each draft through ../local-ai-agent-stack/llm_router.py.

    python outreach.py sample/leads.csv --sender "Your Name" --out out
"""
import argparse
import csv
import json
import os
import re
import sys

DEFAULT_PRICES = {
    "currency": "USD",
    "tiers": {
        "starter": {"pages": 1, "price": 150, "includes": "one-page site, contact button, map and opening hours"},
        "standard": {"pages": 4, "price": 350, "includes": "home, services, gallery and contact pages"},
    },
}
NO_VALUES = {"", "no", "n", "false", "0", "none"}


def load_leads(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = [{k.strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    for need in ("name", "category", "city", "has_website"):
        if rows and need not in rows[0]:
            raise ValueError(f"missing column: {need}")
    return rows


def without_website(leads):
    seen, out = set(), []
    for lead in leads:
        key = (lead["name"].lower(), lead["city"].lower())
        if lead["has_website"].lower() in NO_VALUES and key not in seen:
            seen.add(key)
            out.append(lead)
    return out


def draft_quote(lead, sender, prices=DEFAULT_PRICES):
    cur, tiers = prices["currency"], prices["tiers"]
    lines = "\n".join(f"  - {n.title()} ({t['pages']} page{'s' if t['pages'] > 1 else ''}): "
                      f"{t['price']} {cur}. {t['includes'].capitalize()}." for n, t in tiers.items())
    return (
        f"Subject: A simple website for {lead['name']}\n\n"
        f"Hello {lead['name']} team,\n\n"
        f"I noticed {lead['name']} in {lead['city']} doesn't seem to have a website yet. Many customers "
        f"look up a {lead['category'].lower()} online before visiting, so I'd like to offer to build one for you.\n\n"
        f"Options:\n{lines}\n\n"
        f"If you're interested, reply and I can send a free preview mock-up. "
        f"If this isn't relevant, just let me know and I won't contact you again.\n\n"
        f"Regards,\n{sender}\n"
    )


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "lead"


def run(csv_path, sender, out_dir, prices=DEFAULT_PRICES, polish=None):
    leads = without_website(load_leads(csv_path))
    os.makedirs(out_dir, exist_ok=True)
    summary = []
    for lead in leads:
        text = draft_quote(lead, sender, prices)
        if polish:
            text = polish(text)
        fname = f"{slug(lead['name'])}-{slug(lead['city'])}.txt"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(text)
        summary.append({"name": lead["name"], "city": lead["city"], "email": lead.get("email", ""),
                        "phone": lead.get("phone", ""), "draft_file": fname, "status": "draft"})
    with open(os.path.join(out_dir, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "city", "email", "phone", "draft_file", "status"])
        w.writeheader()
        w.writerows(summary)
    return summary


def make_polisher():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "local-ai-agent-stack"))
    import llm_router

    def polish(text):
        try:
            _, reply = llm_router.ask(
                "Lightly improve the tone of this email. Keep every price, fact and the opt-out sentence unchanged. "
                "Return only the email.\n\n" + text, order=["ollama", "openrouter", "gemini"])
            return reply
        except llm_router.ProviderError:
            return text   # fall back to the template
    return polish


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("leads_csv")
    p.add_argument("--sender", required=True)
    p.add_argument("--out", default="out")
    p.add_argument("--prices", help="JSON file overriding the default price table")
    p.add_argument("--use-llm", action="store_true")
    a = p.parse_args(argv)
    prices = json.load(open(a.prices)) if a.prices else DEFAULT_PRICES
    summary = run(a.leads_csv, a.sender, a.out, prices, make_polisher() if a.use_llm else None)
    print(f"{len(summary)} draft(s) written to {a.out}/ (nothing was sent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
