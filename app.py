import os
import re
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- SCRAPERAPI ADAPTIVE ENGINE ---
def scrape_via_scraperapi(keyword, platform, api_key, limit=20):
    all_items = []
    is_html_scrape = False
    
    if platform == "Amazon":
        endpoints = ["https://api.scraperapi.com/structured/amazon/search"]
        payload = {'api_key': api_key, 'query': keyword, 'country_code': 'us'}
        
    elif platform == "eBay":
        endpoints = [
            "https://api.scraperapi.com/structured/ebay/search",
            "https://api.scraperapi.com/structured/ebay/search/v2"
        ]
        payload = {'api_key': api_key, 'query': keyword, 'country_code': 'us'}
        
    elif platform == "Walmart":
        endpoints = ["https://api.scraperapi.com/structured/walmart/search"]
        payload = {'api_key': api_key, 'query': keyword, 'country_code': 'us'}
        
    elif platform == "Etsy":
        endpoints = ["https://api.scraperapi.com/"]
        payload = {
            'api_key': api_key,
            'url': f'https://www.etsy.com/search?q={keyword.replace(" ", "+")}',
            'render': 'true'
        }
        is_html_scrape = True
    else:
        return []

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, params=payload, timeout=60)
            if response.status_code == 200:
                valid_rank = 1
                
                # HTML PARSING (For Etsy)
                if is_html_scrape:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    listings = soup.find_all('a', class_=re.compile(r'listing-link', re.I))
                    if not listings:
                        listings = soup.find_all('div', class_=re.compile(r'v2-listing-card', re.I))
                        
                    for item in listings:
                        if valid_rank > limit:
                            break
                            
                        a_tag = item if item.name == 'a' else item.find('a')
                        if not a_tag:
                            continue
                            
                        title_tag = item.find('h2') or item.find('h3')
                        if not title_tag:
                            continue
                            
                        title = title_tag.get_text(strip=True)
                        price_tag = item.find(class_=re.compile(r'currency-value'))
                        price = f"${price_tag.get_text(strip=True)}" if price_tag else "Check Site"
                        
                        img_tag = item.find('img')
                        img_url = "https://cdn-icons-png.flaticon.com/512/1170/1170576.png"
                        if img_tag:
                            img_url = img_tag.get('src') or img_tag.get('data-src') or img_url
                            
                        item_link = a_tag.get('href', '')
                        if item_link and not item_link.startswith('http'):
                            item_link = "https://www.etsy.com" + item_link
                            
                        all_items.append({
                            "Platform": platform,
                            "Rank": valid_rank,
                            "Preview": img_url,
                            "Product Title": title.strip(),
                            "Price": price,
                            "Stock Status": "In Stock",
                            "Link": item_link or f"https://www.etsy.com/search?q={keyword}"
                        })
                        valid_rank += 1
                        
                    if all_items:
                        break
                        
                # STRUCTURED JSON PARSING (Amazon, eBay, Walmart)
                else:
                    data = response.json()
                    if isinstance(data, list):
                        results = data
                    else:
                        raw_results = data.get("results", []) or data.get("item_results", [])
                        if isinstance(raw_results, dict):
                            results = raw_results.get("listings", []) or raw_results.get("results", [])
                        else:
                            results = raw_results if isinstance(raw_results, list) else []
                    
                    if results:
                        for item in results:
                            title = item.get("name") or item.get("title") or item.get("product_title")
                            if not title:
                                continue
                                
                            price_raw = item.get("price") or item.get("price_string") or item.get("item_price") or item.get("min_price")
                            
                            if isinstance(price_raw, dict):
                                val = price_raw.get("value") or price_raw.get("amount")
                                curr = price_raw.get("currency", "$")
                                curr_sym = "$" if curr == "USD" else curr
                                price = f"{curr_sym}{val:,.2f}" if val else "Check Site"
                            elif isinstance(price_raw, (int, float)):
                                price = f"${price_raw:,.2f}"
                            else:
                                price = str(price_raw) if price_raw else "Check Site"
                            
                            img_url = item.get("image") or item.get("thumbnail") or item.get("primary_image") or "https://cdn-icons-png.flaticon.com/512/1170/1170576.png"
                            availability = item.get("availability") or item.get("stock_status") or item.get("inventory_status") or "In Stock"
                            
                            fallback_urls = {
                                "eBay": f"https://www.ebay.com/sch/i.html?_nkw={keyword}",
                                "Amazon": f"https://www.amazon.com/s?k={keyword}",
                                "Walmart": f"https://www.walmart.com/search?q={keyword}"
                            }
                            fallback_url = fallback_urls.get(platform, "https://www.google.com")
                            item_link = item.get("url") or item.get("link") or item.get("product_url") or item.get("product_page_url") or fallback_url
                            
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
                        break
            else:
                st.sidebar.warning(f"ℹ️ {platform} returned status: {response.status_code}")
                
        except Exception as e:
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
if st.sidebar.checkbox("Walmart E-Commerce", value=True):
    target_platforms.append("Walmart")
if st.sidebar.checkbox("Etsy Handmade & Vintage", value=True):
    target_platforms.append("Etsy")

results_per_platform = st.sidebar.slider("Target Results Per Platform:", min_value=5, max_value=50, value=15, step=5)

# --- NEW: Dynamic image size controller ---
image_size = st.sidebar.slider(
    "Row / Image Preview Size (px):", 
    min_value=35, 
    max_value=150, 
    value=80, 
    step=5,
    help="Increase to make product preview images larger in the table."
)

st.sidebar.write("---")

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
                
                st.data_editor(
                    df,
                    column_config={
                        # Configured the preview image column width to match the chosen pixel size
                        "Preview": st.column_config.ImageColumn(
                            "Preview", 
                            help="Live product display thumbnails", 
                            width=image_size
                        ),
                        "Product Title": st.column_config.TextColumn("Product Title", width="large"),
                        "Price": st.column_config.TextColumn("Price", width="medium"),
                        "Stock Status": st.column_config.TextColumn("Stock Status", width="medium"),
                        "Link": st.column_config.LinkColumn("Website Link", display_text="Open Page", width="medium"),
                    },
                    use_container_width=True,
                    disabled=True,
                    row_height=image_size  # Enforces a taller row size to prevent the image from scaling down
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
