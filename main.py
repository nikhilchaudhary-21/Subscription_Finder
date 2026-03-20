import csv
import requests
import json
import time
import os
from datetime import datetime

# ============================================================
# CONFIGURATION - Change your settings here
# ============================================================
INPUT_CSV = "meta_ad_output.csv"    # Name of your input CSV file
OUTPUT_CSV = "results_1.csv"        # Name of the output file
DELAY = 1.5                         # Delay between requests (seconds) - to avoid rate limiting
TIMEOUT = 10                        # Request timeout (seconds)
# ============================================================

def check_store_subscriptions(domain, url=None):
    """
    Checks selling_plan_groups on a Shopify store.
    Returns: dict with subscription info
    """
    
    # Clean the domain
    domain = domain.strip().lower()
    domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
    
    base_url = f"https://{domain}"
    
    result = {
        "domain": domain,
        "original_url": url or "",
        "has_subscription": "No",
        "subscription_products": "",
        "product_links": "",
        "selling_plan_count": 0,
        "error": ""
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        # Step 1: Fetch products from products.json
        products_url = f"{base_url}/products.json?limit=250"
        response = requests.get(products_url, headers=headers, timeout=TIMEOUT)
        
        if response.status_code != 200:
            result["error"] = f"HTTP {response.status_code}"
            return result
        
        products_data = response.json()
        products = products_data.get("products", [])
        
        subscription_products = []
        subscription_links = []
        total_selling_plans = 0
        
        # Step 2: Check each product for selling_plan_groups
        for product in products:
            product_handle = product.get("handle", "")
            product_title = product.get("title", "")
            
            # selling_plan_groups is not included in products.json directly —
            # we need to check the individual product page
            product_url = f"{base_url}/products/{product_handle}.js"
            
            try:
                prod_response = requests.get(product_url, headers=headers, timeout=TIMEOUT)
                if prod_response.status_code == 200:
                    prod_data = prod_response.json()
                    selling_plan_groups = prod_data.get("selling_plan_groups", [])
                    
                    if selling_plan_groups and len(selling_plan_groups) > 0:
                        total_selling_plans += len(selling_plan_groups)
                        subscription_products.append(product_title)
                        subscription_links.append(f"{base_url}/products/{product_handle}")
                        
                time.sleep(0.3)  # Small delay between individual product requests
                
            except Exception:
                continue
        
        # Step 3: Compile results
        if subscription_products:
            result["has_subscription"] = "Yes"
            result["subscription_products"] = " | ".join(subscription_products)
            result["product_links"] = " | ".join(subscription_links)
            result["selling_plan_count"] = total_selling_plans
        
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection Error - Store not reachable"
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except json.JSONDecodeError:
        result["error"] = "Not a Shopify store / JSON parse error"
    except Exception as e:
        result["error"] = str(e)
    
    return result


def process_csv(input_file, output_file):
    """
    Read the input CSV, check each store, and save the results.
    """
    
    if not os.path.exists(input_file):
        print(f"❌ ERROR: File '{input_file}' not found!")
        print(f"   Please place it in the same folder as the script: {os.path.abspath(input_file)}")
        return
    
    # Read the input CSV
    stores = []
    with open(input_file, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        
        # Detect if first row is a header
        first_row = next(reader, None)
        if first_row is None:
            print("❌ CSV file is empty!")
            return
        
        # Check if the first row is a header or actual data
        is_header = any(keyword in str(first_row).lower() for keyword in ["domain", "url", "store", "website"])
        
        if is_header:
            print(f"✅ Header detected: {first_row}")
            headers_row = first_row
        else:
            stores.append(first_row)  # First row is data, not a header
            headers_row = None
        
        for row in reader:
            if row:
                stores.append(row)
    
    total = len(stores)
    print(f"\n📊 Total stores to check: {total}")
    print("=" * 60)
    
    # Define output CSV column headers
    output_headers = [
        "Domain",
        "Original URL",
        "Has Subscription (Yes/No)",
        "Subscription Products",
        "Product Links",
        "Total Selling Plans",
        "Error"
    ]
    
    results = []
    yes_count = 0
    no_count = 0
    error_count = 0
    
    start_time = datetime.now()
    
    for i, row in enumerate(stores, 1):
        # Extract domain and URL from the row
        domain = row[0].strip() if len(row) > 0 else ""
        url = row[1].strip() if len(row) > 1 else ""
        
        if not domain:
            continue
        
        print(f"[{i}/{total}] Checking: {domain}...", end=" ", flush=True)
        
        result = check_store_subscriptions(domain, url)
        results.append(result)
        
        # Print status for this store
        if result["error"]:
            print(f"❌ Error: {result['error']}")
            error_count += 1
        elif result["has_subscription"] == "Yes":
            print(f"✅ SUBSCRIPTION FOUND! ({result['selling_plan_count']} plans)")
            yes_count += 1
        else:
            print(f"⭕ No subscription")
            no_count += 1
        
        # Save progress periodically to avoid losing data on crash
        if i % 10 == 0 or i == total:
            save_results(results, output_file, output_headers)
            print(f"   💾 Progress saved ({i}/{total})")
        
        # Delay between stores
        if i < total:
            time.sleep(DELAY)
    
    # Final save
    save_results(results, output_file, output_headers)
    
    # Print summary
    elapsed = datetime.now() - start_time
    print("\n" + "=" * 60)
    print("📈 FINAL SUMMARY")
    print("=" * 60)
    print(f"✅ Has Subscription:    {yes_count}")
    print(f"⭕ No Subscription:     {no_count}")
    print(f"❌ Errors:              {error_count}")
    print(f"📊 Total Checked:       {total}")
    print(f"⏱️  Time taken:          {elapsed}")
    print(f"\n💾 Results saved to: {os.path.abspath(output_file)}")


def save_results(results, output_file, headers):
    """Save results to a CSV file."""
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "domain", "original_url", "has_subscription",
            "subscription_products", "product_links",
            "selling_plan_count", "error"
        ])
        
        # Write custom headers
        f_writer = csv.writer(f)
        # Reopen properly
    
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in results:
            writer.writerow([
                r["domain"],
                r["original_url"],
                r["has_subscription"],
                r["subscription_products"],
                r["product_links"],
                r["selling_plan_count"],
                r["error"]
            ])


if __name__ == "__main__":
    print("🛍️  Shopify Subscription Checker")
    print("=" * 60)
    print(f"📂 Input file:  {INPUT_CSV}")
    print(f"📂 Output file: {OUTPUT_CSV}")
    print(f"⏱️  Delay:       {DELAY}s between stores")
    print("=" * 60)
    
    process_csv(INPUT_CSV, OUTPUT_CSV)
