# Business Outreach Bot

`outreach.py` reads a CSV of local businesses, keeps those **without a website**, removes duplicates, and writes one draft quote email per lead plus `summary.csv`. **It never sends anything**: you review and send drafts yourself.

## Use
```
python outreach.py sample/leads.csv --sender "Your Name" --out out
python outreach.py leads.csv --sender "Your Name" --prices my_prices.json
python outreach.py leads.csv --sender "Your Name" --use-llm    # polish tone via ../local-ai-agent-stack/llm_router.py
```
Leads CSV columns: `name,category,city,has_website[,phone,email]`. Sample data is fake.

## Tests
`python -m unittest discover -s tests`

## Responsible use
- Every draft includes an opt-out line; honour it
- Check cold-email and data-protection rules where you and the recipient live before sending
- Don't commit real lead data (`data/` and `out/` are best kept local)

## Not done yet
- Finding leads automatically (needs a data source you are permitted to use)
- Sending and reply tracking
