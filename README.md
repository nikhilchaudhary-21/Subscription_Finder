# Shopify Subscription Checker

A Python script that reads a list of Shopify store domains from a CSV file and checks whether each store offers **subscription-based products** (via Shopify's `selling_plan_groups` API).

---

## What It Does

For each store domain in the input CSV, the script:

1. Fetches the store's full product list from `/products.json`
2. Checks each product's `.js` endpoint for `selling_plan_groups`
3. Records which products have subscription plans and how many plans they offer
4. Saves results progressively (every 10 stores) to avoid data loss on crashes
5. Prints a final summary of how many stores have/don't have subscriptions

---

## Input Requirements

A CSV file (default: `meta_ad_output.csv`) where:
- **Column 1**: Store domain (e.g. `mystore.com` or `https://mystore.com`)
- **Column 2** *(optional)*: Original URL for reference

The script auto-detects whether the first row is a header or data.

**Example:**
```
domain
mystore.com
another-brand.com,
```

---

## Output

A CSV file (default: `results_1.csv`) with these columns:

| Column | Description |
|---|---|
| `Domain` | Cleaned store domain |
| `Original URL` | URL from the input file (if provided) |
| `Has Subscription (Yes/No)` | Whether any subscription products were found |
| `Subscription Products` | Names of products with subscriptions (pipe-separated) |
| `Product Links` | Direct links to those products (pipe-separated) |
| `Total Selling Plans` | Total number of selling plan groups found across all products |
| `Error` | Error message if the store could not be checked |

---

## Configuration

Edit these lines at the top of the script:

```python
INPUT_CSV = "meta_ad_output.csv"   # Your input file name
OUTPUT_CSV = "results_1.csv"       # Your output file name
DELAY = 1.5                        # Seconds to wait between stores (avoid rate limiting)
TIMEOUT = 10                       # Max seconds to wait for a response
```

---

## Requirements

```
requests
```

Install with:

```bash
pip install requests
```

---

## Usage

1. Place the script and your input CSV in the same folder
2. Update `INPUT_CSV` if your file has a different name
3. Run:

```bash
python shopify_subscription_checker.py
```

Progress is printed live and auto-saved every 10 stores.

---

## How the Subscription Check Works

Shopify's `/products.json` endpoint does **not** include `selling_plan_groups` in its response. The script works around this by:

1. Getting all product handles from `/products.json`
2. Fetching each product individually via `/products/{handle}.js`
3. Checking if the `selling_plan_groups` array is non-empty

This is the only reliable way to detect subscriptions through Shopify's public (unauthenticated) API.

> **Note:** Because each product requires a separate request, checking a large store (250 products) will take approximately 75–100 seconds per store at the default settings.

---

## Error Types

| Error | Meaning |
|---|---|
| `HTTP 4xx / 5xx` | Store returned an error (may be private, password-protected, or down) |
| `Connection Error - Store not reachable` | Domain does not resolve or is offline |
| `Timeout` | Store took too long to respond |
| `Not a Shopify store / JSON parse error` | The URL does not appear to be a Shopify store |

---

## Notes

- The script saves progress every 10 stores — if it crashes, you won't lose all your work
- Domains with `https://` or trailing slashes are automatically cleaned
- The output file uses UTF-8 BOM encoding (`utf-8-sig`) for clean display in Excel
