Import os
import streamlit as st
import pandas as pd
import requests

# --- SCRAPERAPI ADAPTIVE ENGINE ---
def scrape_via_scraperapi(keyword, platform, api_key, limit=20):
    all_items = []
    
    # Adaptive endpoint detection for account variations
    if platform == "Amazon":
        endpoints = ["https://api.scraperapi.com/structured/amazon/search"]
    elif platform == "eBay":
        endpoints = [
            "https://api.scraperapi.com/structured/ebay/search",
            "https://api.scraperapi.com/structured/ebay/search/v2"
        ]
    else:
        return []

    payload = {
        'api_key': api_key,
        'query': keyword,
        'country_code': 'us'
    }
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, params=payload, timeout=45)
            if response.status_code == 200:
                data = response.json()
                
                # 1. SAFELY HANDLE LISTS VS DICTIONARIES
                if isinstance(data, list):
                    # eBay returns a flat list natively
                    results = data
                else:
                    # Amazon returns a dict containing a 'results' array
                    raw_results = data.get("results", [])
                    if isinstance(raw_results, dict):
                        results = raw_results.get("listings", []) or raw_results.get("results", [])
                    else:
                        results = raw_results if isinstance(raw_results, list) else []
                
                if results:
                    valid_rank = 1
                    for item in results:
                        # 2. ADAPT KEYS FOR EBAY (product_title) vs AMAZON (name, title)
                        title = item.get("name") or item.get("title") or item.get("product_title")
                        if not title:
                            continue
                            
                        # 3. HANDLE NESTED PRICE DICTIONARIES
                        price_raw = item.get("price") or item.get("price_string") or item.get("item_price")
                        
                        if isinstance(price_raw, dict):
                            # Unpack eBay price object: {"value": 149.99, "currency": "USD"}
                            val = price_raw.get("value")
                            curr = price_raw.get("currency", "$")
                            curr_sym = "$" if curr == "USD" else curr
                            price = f"{curr_sym}{val:,.2f}" if val else "Check Site"
                        elif isinstance(price_raw, (int, float)):
                            price = f"${price_raw:,.2f}"
                        else:
                            price = str(price_raw) if price_raw else "Check Site"
                        
                        img_url = item.get("image") or item.get("thumbnail") or "https://cdn-icons-png.flaticon.com/512/1170/1170576.png"
                        availability = item.get("availability") or item.get("stock_status") or "In Stock"
                        
                        # Fallback link structure if explicit keys are blank
                        fallback_url = f"https://www.ebay.com/sch/i.html?_nkw={keyword}" if platform == "eBay" else f"https://www.amazon.com/s?k={keyword}"
                        
                        # Look for product_url (eBay specific)
                        item_link = item.get("url") or item.get("link") or item.get("product_url") or fallback_url
                        
                        all_items.append({
                            "Platform": platform,
                            "Rank": valid_rank,
                            "Preview": img_url,
                            "Product Title": title.strip(),
                            "Price": price,
                            "Stock Status": availability.replace("_", " ").title() if isinstance(availability, str) else "In Stock",
                            "Link": item_link
                        })
                        
                        valid_rank += 1
                        if valid_rank > limit:
                            break
                    
                    if all_items:
                        break # Successfully populated data, skip alternative endpoints
            else:
                st.sidebar.warning(f"ℹ️ {platform} try variant returned status: {response.status_code}")
                
        except Exception as e:
            # Printing the error allows you to see issues in your terminal rather than them being silently skipped
            print(f"Error scraping {platform}: {e}") 
            continue
            
    return all_items

# --- RENDER BACKUP SYSTEM VECTOR ---
def run_legacy_fallback(search_keyword, platform, target_ceiling):
    results = []
    for rank in range(1, target_ceiling + 1):
        results.append({
            "Platform": platform,
            "Rank": rank,
            "Preview": "https://cdn-icons-png.flaticon.com/512/1170/1170576.png",
            "Product Title": f"Sample {platform} Item #{rank} for '{search_keyword}'",
            "Price": "[Requires API Key]",
            "Stock Status": "[Requires API Key]",
            "Link": "https://www.google.com"
        })
    return results

# --- STREAMLIT EXECUTIVE INTERFACE ---
st.set_page_config(page_title="Enterprise Market Scraper", page_icon="📈", layout="wide")

st.sidebar.header("⚙️ System Configuration")
st.sidebar.write("Configure your extraction credentials below.")

client_proxy_key = st.sidebar.text_input(
    "Premium Proxy API Key:", 
    type="password", 
    placeholder="Paste ScraperAPI key here..."
)

if client_proxy_key:
    st.sidebar.success("✅ Deep Matrix Direct Routing Active.")
else:
    st.sidebar.warning("⚠️ Running via offline legacy mode (No Live Metrics).")

st.sidebar.write("---")

target_platforms = []
if st.sidebar.checkbox("Amazon Marketplace", value=True):
    target_platforms.append("Amazon")
if st.sidebar.checkbox("eBay Auctions", value=True):
    target_platforms.append("eBay")

results_per_platform = st.sidebar.slider("Target Results Per Platform:", min_value=5, max_value=50, value=15, step=5)

st.title("📈 Enterprise E-Commerce Data Workspace")
st.write("On-demand marketplace extraction engine for competitive intelligence and retail data sheets.")

client_keyword = st.text_input("Enter Focus Product Keyword:", placeholder="e.g., Xiaomi phone")

if st.button("⚡ Execute Automated Mining Sequence"):
    if not target_platforms:
        st.error("Please check at least one source channel in the settings sidebar.")
    elif client_keyword:
        with st.spinner("Processing deep channel indexing vectors via ScraperAPI..."):
            
            master_dataset = []
            
            for platform in target_platforms:
                if client_proxy_key:
                    platform_data = scrape_via_scraperapi(
                        keyword=client_keyword,
                        platform=platform,
                        api_key=client_proxy_key,
                        limit=results_per_platform
                    )
                    master_dataset.extend(platform_data)
                else:
                    platform_data = run_legacy_fallback(client_keyword, platform, results_per_platform)
                    master_dataset.extend(platform_data)
            
            if master_dataset:
                st.success(f"✨ Successfully compiled {len(master_dataset)} marketplace records!")
                
                df = pd.DataFrame(master_dataset)
                
                # Enhanced config featuring functional click-to-open Link Columns
                st.data_editor(
                    df,
                    column_config={
                        "Preview": st.column_config.ImageColumn("Preview", help="Live product display thumbnails"),
                        "Product Title": st.column_config.TextColumn("Product Title", width="large"),
                        "Price": st.column_config.TextColumn("Price", width="medium"),
                        "Stock Status": st.column_config.TextColumn("Stock Status", width="medium"),
                        "Link": st.column_config.LinkColumn("Website Link", display_text="Open Page", width="medium"),
                    },
                    use_container_width=True,
                    disabled=True
                )
                
                csv_file = df.to_csv(index=False).encode('utf-8')
                st.write("---")
                st.download_button(
                    label="📥 Export Compiled Excel/CSV Dataset",
                    data=csv_file,
                    file_name=f"{client_keyword.replace(' ', '_')}_market_intelligence.csv",
                    mime="text/csv"
                )
            else:
                st.error("The API request returned no records from the active providers. Verify remaining credit balances.")
    else:
        st.error("Please enter a focus product keyword target to begin.")

