import os
import re
import json
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

SCRAPERAPI_ENDPOINT = "https://api.scraperapi.com/"


def extract_image_url(image_field):
    """
    Normalize a schema.org `image` value into a plain URL string.
    """
    if isinstance(image_field, list):
        image_field = image_field[0] if image_field else None

    if isinstance(image_field, dict):
        image_field = image_field.get('url') or image_field.get('contentUrl') or image_field.get('value')

    if isinstance(image_field, str) and image_field:
        if image_field.startswith('//'):
            return f'https:{image_field}'
        return image_field

    return None


def find_product_node(data):
    """
    Recursively search for any dictionary inside lists or dicts that
    contains '@type': 'Product' to support complex JSON-LD structures.
    """
    if isinstance(data, dict):
        if data.get('@type') == 'Product':
            return data
        for val in data.values():
            result = find_product_node(val)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_product_node(item)
            if result:
                return result
    return None


# --- GENERAL PURPOSE HTML FETCH ROUTER ---
def fetch_page_html(target_url, provider, api_key):
    """
    Unified helper to fetch raw HTML from any URL using a selected general-purpose provider.
    Supports ScraperAPI, Scrape.do, and ScrapingBee.
    """
    if provider == "ScraperAPI":
        payload = {
            'api_key': api_key,
            'url': target_url,
            'country_code': 'us',
            'premium': 'true'
        }
        try:
            resp = requests.get(SCRAPERAPI_ENDPOINT, params=payload, timeout=70)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            print(f"ScraperAPI error fetching {target_url}: {e}")
            
    elif provider == "Scrape.do":
        payload = {
            'token': api_key,
            'url': target_url,
            'super': 'true'  # Uses residential/premium proxies to bypass strict blocks
        }
        try:
            resp = requests.get("https://api.scrape.do/", params=payload, timeout=70)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            print(f"Scrape.do error fetching {target_url}: {e}")
            
    elif provider == "ScrapingBee":
        payload = {
            'api_key': api_key,
            'url': target_url,
            'render_js': 'false'  # Set to false to consume only 1 credit per request
        }
        try:
            resp = requests.get("https://app.scrapingbee.com/api/v1/", params=payload, timeout=70)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            print(f"ScrapingBee error fetching {target_url}: {e}")
            
    return None


# --- GENERAL PURPOSE HTML SEARCH PARSERS ---
def parse_amazon_search_html(html, limit=20):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    containers = soup.select('div[data-component-type="s-search-result"]')
    if not containers:
        containers = soup.select('.s-result-item')

    rank = 1
    for container in containers:
        title_el = container.select_one('h2 a span') or container.select_one('.a-size-medium') or container.select_one('.a-size-base-plus')
        if not title_el:
            continue
        title = title_el.text.strip()

        price_el = container.select_one('.a-price .a-offscreen')
        price = price_el.text.strip() if price_el else "Check Site"

        img_el = container.select_one('img.s-image')
        img_url = img_el.get('src') if img_el else "https://cdn-icons-png.flaticon.com/512/1170/1170576.png"

        link_el = container.select_one('h2 a') or container.select_one('a.a-link-normal')
        link = "https://www.amazon.com" + link_el.get('href') if link_el and link_el.get('href', '').startswith('/') else (link_el.get('href') if link_el else "#")

        items.append({
            "Platform": "Amazon",
            "Rank": rank,
            "Preview": img_url,
            "Product Title": title,
            "Price": price,
            "Stock Status": "In Stock",
            "Link": link
        })
        rank += 1
        if rank > limit:
            break
    return items


def parse_ebay_search_html(html, limit=20):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    containers = soup.select('.srp-results .s-item') or soup.select('.s-item')
    rank = 1
    for container in containers:
        title_el = container.select_one('.s-item__title')
        if not title_el or "shop on ebay" in title_el.text.lower():
            continue
        title = title_el.text.strip()

        price_el = container.select_one('.s-item__price')
        price = price_el.text.strip() if price_el else "Check Site"

        img_el = container.select_one('.s-item__image-img') or container.select_one('img')
        img_url = img_el.get('src') or img_el.get('data-src') if img_el else "https://cdn-icons-png.flaticon.com/512/1170/1170576.png"

        link_el = container.select_one('.s-item__link')
        link = link_el.get('href').split('?')[0] if link_el and link_el.get('href') else "#"

        items.append({
            "Platform": "eBay",
            "Rank": rank,
            "Preview": img_url,
            "Product Title": title,
            "Price": price,
            "Stock Status": "In Stock",
            "Link": link
        })
        rank += 1
        if rank > limit:
            break
    return items


def parse_walmart_search_html(html, limit=20):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    containers = soup.select('div[data-testid="item-card"]') or soup.select('[data-item-id]')
    rank = 1
    for container in containers:
        title_el = container.select_one('[data-automation-id="product-title"]') or container.select_one('.w_iUH7')
        if not title_el:
            continue
        title = title_el.text.strip()

        price_el = container.select_one('[data-automation-id="product-price"]') or container.select_one('.w_mSgX')
        price = price_el.text.strip().replace("current price ", "") if price_el else "Check Site"

        img_el = container.select_one('img')
        img_url = img_el.get('src') if img_el else "https://cdn-icons-png.flaticon.com/512/1170/1170576.png"

        link_el = container.select_one('a')
        link = "https://www.walmart.com" + link_el.get('href') if link_el and link_el.get('href', '').startswith('/') else (link_el.get('href') if link_el else "#")

        items.append({
            "Platform": "Walmart",
            "Rank": rank,
            "Preview": img_url,
            "Product Title": title,
            "Price": price,
            "Stock Status": "In Stock",
            "Link": link
        })
        rank += 1
        if rank > limit:
            break
    return items


def parse_etsy_search_html(html, limit=20):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    containers = soup.select('.search-listings-group-col .wt-list-unstyled li') or soup.select('.wt-grid .wt-list-unstyled li') or soup.select('.search-listings-group li')
    if not containers:
        containers = soup.select('li.wt-list-unstyled') or soup.select('li[data-search-results-listing-card]') or soup.select('.v2-listing-card')

    rank = 1
    for container in containers:
        title_el = container.select_one('h3.wt-text-caption') or container.select_one('.v2-listing-card__title') or container.select_one('h3')
        if not title_el:
            continue
        title = title_el.text.strip()

        price_el = container.select_one('.lc-price') or container.select_one('.currency-value') or container.select_one('.n-listing-card__price') or container.select_one('.wt-text-title-01')
        price = price_el.text.strip() if price_el else "Check Site"

        img_el = container.select_one('img')
        img_url = "https://cdn-icons-png.flaticon.com/512/1170/1170576.png"
        if img_el:
            img_url = img_el.get('src') or img_el.get('data-src') or img_el.get('data-origin-src') or img_url

        link_el = container.select_one('a.listing-link') or container.select_one('a')
        link = link_el.get('href').split('?')[0] if link_el and link_el.get('href') else "#"
        if link.startswith('/'):
            link = "https://www.etsy.com" + link

        items.append({
            "Platform": "Etsy",
            "Rank": rank,
            "Preview": img_url,
            "Product Title": title,
            "Price": price,
            "Stock Status": "In Stock",
            "Link": link
        })
        rank += 1
        if rank > limit:
            break
    return items


# --- PLATFORM SEARCH ROUTER ---
def scrape_structured(keyword, platform, api_key, limit=20, provider="ScraperAPI"):
    if provider == "ScraperAPI":
        if platform == "Amazon":
            endpoints = ["https://api.scraperapi.com/structured/amazon/search"]
            payloads = [{'api_key': api_key, 'query': keyword, 'country_code': 'us'}]
        elif platform == "eBay":
            endpoints = [
                "https://api.scraperapi.com/structured/ebay/search",
                "https://api.scraperapi.com/structured/ebay/search/v2"
            ]
            payloads = [{'api_key': api_key, 'query': keyword, 'country_code': 'us'}] * len(endpoints)
        elif platform == "Walmart":
            endpoints = ["https://api.scraperapi.com/structured/walmart/search"]
            payloads = [{'api_key': api_key, 'query': keyword, 'country_code': 'us'}]
        else:
            return []

        for endpoint, payload in zip(endpoints, payloads):
            try:
                response = requests.get(endpoint, params=payload, timeout=70)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        results = data
                    else:
                        raw_results = (
                            data.get("items", [])
                            or data.get("results", [])
                            or data.get("item_results", [])
                        )
                        if isinstance(raw_results, dict):
                            results = raw_results.get("listings", []) or raw_results.get("results", [])
                        else:
                            results = raw_results if isinstance(raw_results, list) else []

                    valid_rank = 1
                    all_items = []
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
                        return all_items
            except Exception as e:
                print(f"Error scraping structured {platform} via ScraperAPI: {e}")
                continue

        # --- AUTO-FALLBACK TO DIRECT HTML CRAWLING FOR SCRAPERAPI ---
        if platform == "Amazon":
            target_url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"
            html = fetch_page_html(target_url, "ScraperAPI", api_key)
            if html:
                return parse_amazon_search_html(html, limit)
        elif platform == "eBay":
            target_url = f"https://www.ebay.com/sch/i.html?_nkw={keyword.replace(' ', '+')}"
            html = fetch_page_html(target_url, "ScraperAPI", api_key)
            if html:
                return parse_ebay_search_html(html, limit)
        elif platform == "Walmart":
            target_url = f"https://www.walmart.com/search?q={keyword.replace(' ', '+')}"
            html = fetch_page_html(target_url, "ScraperAPI", api_key)
            if html:
                return parse_walmart_search_html(html, limit)

    else:
        if platform == "Amazon":
            target_url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"
            html = fetch_page_html(target_url, provider, api_key)
            if html:
                return parse_amazon_search_html(html, limit)
        elif platform == "eBay":
            target_url = f"https://www.ebay.com/sch/i.html?_nkw={keyword.replace(' ', '+')}"
            html = fetch_page_html(target_url, provider, api_key)
            if html:
                return parse_ebay_search_html(html, limit)
        elif platform == "Walmart":
            target_url = f"https://www.walmart.com/search?q={keyword.replace(' ', '+')}"
            html = fetch_page_html(target_url, provider, api_key)
            if html:
                return parse_walmart_search_html(html, limit)

    return []


# --- ETSY DIRECT SEARCH OR SCAPERAPI DISCOVERY ---
def scrape_etsy(keyword, api_key, limit=20, provider="ScraperAPI"):
    if provider == "ScraperAPI":
        payload = {
            'api_key': api_key,
            'query': f'site:etsy.com/listing {keyword}',
            'country_code': 'us'
        }
        listing_urls = []
        try:
            resp = requests.get("https://api.scraperapi.com/structured/google/search", params=payload, timeout=70)
            if resp.status_code == 200:
                data = resp.json()
                seen = set()
                for result in data.get("organic_results", []):
                    link = result.get("link", "")
                    if "etsy.com/listing" in link:
                        clean_url = link.split('?')[0]
                        if clean_url not in seen:
                            seen.add(clean_url)
                            listing_urls.append(clean_url)
        except Exception as e:
            print(f"Etsy discovery failed: {e}")

        if not listing_urls:
            search_url = f'https://www.etsy.com/search?q={keyword.replace(" ", "+")}'
            html = fetch_page_html(search_url, provider, api_key)
            if html:
                found = re.findall(r'https://www\.etsy\.com/listing/\d+(?:/[^"\'s\\%]+)?', html)
                seen = set()
                for url in found:
                    clean_url = url.split('?')[0]
                    if clean_url not in seen:
                        seen.add(clean_url)
                        listing_urls.append(clean_url)

        all_items = []
        for rank, listing_url in enumerate(listing_urls[:limit], start=1):
            detail_payload = {'api_key': api_key, 'url': listing_url, 'country_code': 'us', 'premium': 'true'}
            try:
                resp = requests.get(SCRAPERAPI_ENDPOINT, params=detail_payload, timeout=70)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    ld_data = None
                    for script in soup.find_all('script', attrs={'type': 'application/ld+json'}):
                        if not script.string:
                            continue
                        try:
                            parsed = json.loads(script.string)
                        except (json.JSONDecodeError, TypeError):
                            continue

                        ld_data = find_product_node(parsed)
                        if ld_data:
                            break

                    title = None
                    if ld_data:
                        title = ld_data.get('name')
                    if not title:
                        og_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'twitter:title'})
                        title = og_title.get('content') if og_title else 'Etsy Item'

                    price = "Check Site"
                    if ld_data:
                        offers = ld_data.get('offers', {})
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        price_val = offers.get('price')
                        curr = offers.get('priceCurrency', 'USD')
                        curr_sym = "$" if curr == "USD" else curr
                        price = f"{curr_sym}{float(price_val):,.2f}" if price_val else "Check Site"

                    img_url = extract_image_url(ld_data.get('image')) if ld_data else None
                    if not img_url:
                        og_image = soup.find('meta', property='og:image')
                        img_url = og_image.get('content') if og_image else "https://cdn-icons-png.flaticon.com/512/1170/1170576.png"

                    all_items.append({
                        "Platform": "Etsy",
                        "Rank": rank,
                        "Preview": img_url,
                        "Product Title": title.strip(),
                        "Price": price,
                        "Stock Status": "In Stock",
                        "Link": listing_url
                    })
            except Exception as e:
                continue

        if not all_items:
            target_url = f"https://www.etsy.com/search?q={keyword.replace(' ', '+')}"
            html = fetch_page_html(target_url, provider, api_key)
            if html:
                return parse_etsy_search_html(html, limit)
        else:
            return all_items

    else:
        target_url = f"https://www.etsy.com/search?q={keyword.replace(' ', '+')}"
        html = fetch_page_html(target_url, provider, api_key)
        if html:
            return parse_etsy_search_html(html, limit)

    return []


# --- RENDER BACKUP SYSTEM VECTOR (MOCK DATA) ---
def run_legacy_fallback(search_keyword, platform, target_ceiling):
    results = []
    sanitized_keyword = re.sub(r'[^a-zA-Z0-9]', '', search_keyword) or "product"

    for rank in range(1, target_ceiling + 1):
        fallback_img = f"https://cdn-icons-png.flaticon.com/512/3081/3081162.png"
        mock_price = f"${(rank * 12.49 + 9.99):,.2f}"
        mock_stock = "In Stock" if rank % 4 != 0 else "Low Stock"

        results.append({
            "Platform": platform,
            "Rank": rank,
            "Preview": fallback_img,
            "Product Title": f"{platform} {search_keyword.title()} - Premium Model {rank}",
            "Price": mock_price,
            "Stock Status": mock_stock,
            "Link": f"https://www.google.com/search?q={search_keyword}"
        })
    return results


# --- STREAMLIT EXECUTIVE INTERFACE ---
st.set_page_config(page_title="Enterprise Market Scraper", page_icon="📈", layout="wide")

st.sidebar.header("⚙️ System Configuration")
st.sidebar.write("Configure your extraction credentials below.")

api_provider = st.sidebar.selectbox("Active Proxy Provider:", ["ScraperAPI", "Scrape.do", "ScrapingBee"])

client_proxy_key = st.sidebar.text_input(
    f"Paste {api_provider} API Key / Token:",
    type="password",
    placeholder="Paste API credential here...",
    key="proxy_api_key_input"
)

if client_proxy_key:
    st.sidebar.success(f"✅ {api_provider} Routing Active.")
else:
    st.sidebar.warning("⚠️ Running via offline legacy mode (No Live Metrics).")

st.sidebar.write("---")

st.sidebar.subheader("🛒 Store Selection")

# Initialize checkbox default values in session state (only runs once)
if "chk_amazon" not in st.session_state:
    st.session_state.chk_amazon = True
if "chk_ebay" not in st.session_state:
    st.session_state.chk_ebay = True
if "chk_walmart" not in st.session_state:
    st.session_state.chk_walmart = True
if "chk_etsy" not in st.session_state:
    st.session_state.chk_etsy = True

# Bind checkboxes exclusively to their state keys. 
# This completely fixes the inability to check/uncheck them.
platform_amazon = st.sidebar.checkbox("Amazon Marketplace", key="chk_amazon")
platform_ebay = st.sidebar.checkbox("eBay Auctions", key="chk_ebay")
platform_walmart = st.sidebar.checkbox("Walmart E-Commerce", key="chk_walmart")
platform_etsy = st.sidebar.checkbox("Etsy Handmade & Vintage", key="chk_etsy")

target_platforms = []
if platform_amazon:
    target_platforms.append("Amazon")
if platform_ebay:
    target_platforms.append("eBay")
if platform_walmart:
    target_platforms.append("Walmart")
if platform_etsy:
    target_platforms.append("Etsy")

results_per_platform = st.sidebar.slider("Target Results Per Platform:", min_value=5, max_value=50, value=15, step=5)

image_size = st.sidebar.slider(
    "Row / Image Preview Size (px):",
    min_value=35,
    max_value=150,
    value=80,
    step=5,
    help="Increase to make product preview images larger in the table below."
)

st.sidebar.write("---")

st.title("📈 Enterprise E-Commerce Data Workspace")
st.write("On-demand marketplace extraction engine for competitive intelligence and retail data sheets.")

client_keyword = st.text_input("Enter Focus Product Keyword:", placeholder="e.g., Xiaomi phone")

if st.button("⚡ Execute Automated Mining Sequence"):
    if not target_platforms:
        st.error("Please check at least one source channel in the settings sidebar.")
    elif client_keyword:
        with st.spinner(f"Processing deep channel indexing vectors via {api_provider}..."):

            master_dataset = []

            for platform in target_platforms:
                if client_proxy_key:
                    if platform == "Etsy":
                        platform_data = scrape_etsy(
                            keyword=client_keyword,
                            api_key=client_proxy_key,
                            limit=results_per_platform,
                            provider=api_provider
                        )
                    else:
                        platform_data = scrape_structured(
                            keyword=client_keyword,
                            platform=platform,
                            api_key=client_proxy_key,
                            limit=results_per_platform,
                            provider=api_provider
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
                    row_height=image_size
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
                st.error("The API request returned no records from the active providers. Verify remaining credit balances or query limits.")
    else:
        st.error("Please enter a focus product keyword target to begin.")