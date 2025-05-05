from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import logging
import concurrent.futures
import time
import os
# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

def scrape_medicines(search_term):
    # --- Configuration ---
    MAX_RESULTS = 3  # Limit to top 3 results per website
    TIMEOUT_SHORT = 15  # Short timeout for initial check (seconds)
    TIMEOUT_LONG = 30  # Longer timeout for actual scraping (seconds)

    # --- Selenium Setup ---
    def create_driver():
        options = webdriver.ChromeOptions()
        prefs = {"profile.managed_default_content_settings.images": 2}  # Disable images
        options.add_experimental_option("prefs", prefs)
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')  # Add this line
        options.add_argument('--blink-settings=imagesEnabled=false')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        # For cloud deployment
        if 'RENDER' in os.environ:
            options.add_argument('--disable-dev-shm-usage')  # Changed from chrome_options to options
            options.add_argument('--remote-debugging-port=9222')  # Changed from chrome_options to options
            return webdriver.Chrome(options=options)
        else:
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # --- Apollo Pharmacy Scraper ---
    def scrape_apollo(search_term):
        driver = None
        try:
            driver = create_driver()
            driver.set_page_load_timeout(TIMEOUT_LONG)
            url = f"https://www.apollopharmacy.in/search-medicines/{search_term}"
            product_card_selector = 'div[class*="ProductCard_productCard"]'
            
            # Quick check if products exist
            driver.get(url)
            try:
                # Use shorter timeout for initial check
                WebDriverWait(driver, TIMEOUT_SHORT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, product_card_selector))
                )
            except Exception as e:
                logging.info(f"No products found on Apollo for {search_term}: {str(e)}")
                return []
                
            # If we get here, products exist, so proceed with full scraping
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            product_cards = soup.select(product_card_selector)[:MAX_RESULTS]

            results = []
            for i, card in enumerate(product_cards, 1):
                name_element = card.select_one('h2.Rb') or card.select_one('h2')
                quantity_element = card.select_one('h2:not(.Rb)')
                price_element = card.select_one('p.Pb.wf') or card.select_one('div[class*="Ob"] p')
                link_element = card.select_one('a[href]')

                name_text = name_element.get_text(strip=True) if name_element else "Name not found"
                quantity_text = quantity_element.get_text(strip=True) if quantity_element else "Quantity not found"
                price_text = price_element.get_text(strip=True) if price_element else "Price not found"
                product_link = f"https://www.apollopharmacy.in{link_element['href']}" if link_element and link_element.get('href') else "Link not found"

                # Clean price text
                price_match = re.search(r'₹\s*\d+\.?\d*', price_text)
                price_text = price_match.group(0) if price_match else "Price not found"

                results.append({
                    'number': i,
                    'medicine': name_text,
                    'quantity': quantity_text,
                    'price': price_text,
                    'link': product_link
                })
            return results
        except Exception as e:
            logging.error(f"Error in scrape_apollo: {str(e)}")
            return []
        finally:
            if driver:
                driver.quit()

    # --- Netmeds Scraper ---
    def scrape_netmeds(search_term):
        driver = None
        try:
            driver = create_driver()
            driver.set_page_load_timeout(TIMEOUT_LONG)
            url = f"https://www.netmeds.com/catalogsearch/result/{search_term}/all"
            product_box_selector = 'div.cat-item'
            
            # Quick check if products exist
            driver.get(url)
            try:
                # Use shorter timeout for initial check
                WebDriverWait(driver, TIMEOUT_SHORT).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_box_selector))
                )
            except Exception as e:
                logging.info(f"No products found on Netmeds for {search_term}: {str(e)}")
                return []
                
            # If we get here, products exist, so proceed with full scraping
            name_selector = 'h3.clsgetname'
            price_box_selector = 'span.price-box'
            
            soup = BeautifulSoup(driver.page_source, 'lxml')
            product_boxes = soup.select(product_box_selector)[:MAX_RESULTS]

            results = []
            for i, product_box in enumerate(product_boxes, 1):
                # Rest of the Netmeds scraping code remains the same
                med_name_tag = product_box.select_one(name_selector)
                link_element = product_box.select_one('a[href]')
                med_name_text = med_name_tag.text.strip() if med_name_tag else "Name not found"
                quantity_text = "Quantity not found"
                medicine_name = med_name_text

                if med_name_text != "Name not found":
                    quantity_regex = re.compile(
                        r'\s+('
                        r'(?:\d+\s*)?'
                        r'(?:gm|g|ml|m?l|tablets?|capsules?|strips?|sachets?|units?|pc|pkt|kit|pair|each|bottles?|tubes?|packs?|suspension|syrup|cream|ointment|gel|solution|drops|injection|vial|jar|can|box|blister|spray|pouch|wipe|pad|roll|sheet|disc|patch|kit|combipack|applicator|cartridge|refill|ampoule|aerosol|pessary|suppository|lozenge|pastille|powder|granule|flake|pellet|wafer|film|implant|insert|ring|coil|sponge|tampon|diaphragm|condom|pump|inhaler|nebulizer|syringe|needle|catheter|bag|Pack of)\b'
                        r'.*)'
                        r'\s*$',
                        re.IGNORECASE
                    )
                    quantity_match = quantity_regex.search(med_name_text)
                    if quantity_match:
                        quantity_text = quantity_match.group(1).strip()
                        medicine_name = med_name_text[:quantity_match.start(0)].strip()

                price_box = product_box.select_one(price_box_selector)
                price_text = "Price not found"
                if price_box:
                    potential_price_elements = price_box.select('span, div, p')
                    for element in potential_price_elements:
                        element_text = element.text.strip()
                        price_match = re.search(r'₹\s*\d+\.?\d*', element_text)
                        if price_match:
                            price_text = price_match.group(0)
                            break
                    else:
                        price_box_text = price_box.text.strip()
                        price_match_fallback = re.search(r'₹\s*\d+\.?\d*', price_box_text)
                        if price_match_fallback:
                            price_text = price_match_fallback.group(0)

                product_link = f"https://www.netmeds.com{link_element['href']}" if link_element and link_element.get('href') else "Link not found"

                results.append({
                    'number': i,
                    'medicine': medicine_name,
                    'quantity': quantity_text,
                    'price': price_text,
                    'link': product_link
                })
            return results
        except Exception as e:
            logging.error(f"Error in scrape_netmeds: {str(e)}")
            return []
        finally:
            if driver:
                driver.quit()

    # --- 1mg Scraper ---
    def scrape_1mg(search_term):
        driver = None
        try:
            driver = create_driver()
            driver.set_page_load_timeout(TIMEOUT_LONG)
            url = f"https://www.1mg.com/search/all?name={search_term}"
            L1_CARD_SELECTOR = 'div[class*="style__product-box"]'
            L2_CARD_SELECTOR = 'div[class*="style__horizontal-card"]'
            
            # Quick check if products exist
            driver.get(url)
            try:
                # Use shorter timeout for initial check
                WebDriverWait(driver, TIMEOUT_SHORT).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, L1_CARD_SELECTOR)) > 0 or
                              len(d.find_elements(By.CSS_SELECTOR, L2_CARD_SELECTOR)) > 0
                )
            except Exception as e:
                logging.info(f"No products found on 1mg for {search_term}: {str(e)}")
                return []
                
            # If we get here, products exist, so proceed with full scraping
            L1_NAME_SELECTOR = 'div[class*="style__pro-title"]'
            L1_QUANTITY_SELECTOR = 'div[class*="style__pack-size"]'
            L1_PRICE_SELECTOR = 'div[class*="style__price-tag"]'
            L1_MRP_SELECTOR = 'div[class*="style__mrp-tag"]'
            L1_LINK_SELECTOR = 'a[href]'
            L2_NAME_SELECTOR = 'span[class*="style__pro-title"]'
            L2_QUANTITY_SELECTOR = 'div[class*="style__pack-size"]'
            L2_PRICE_SELECTOR = 'div[class*="style__price-tag"]'
            L2_MRP_SELECTOR = 'div[class*="style__mrp-tag"]'
            L2_LINK_SELECTOR = 'a[href]'

            soup = BeautifulSoup(driver.page_source, 'lxml')
            layout1_cards = soup.select(L1_CARD_SELECTOR)
            layout2_cards = soup.select(L2_CARD_SELECTOR)

            if layout1_cards:
                cards_to_process = layout1_cards[:MAX_RESULTS]
                selected_name_selector = L1_NAME_SELECTOR
                selected_quantity_selector = L1_QUANTITY_SELECTOR
                selected_price_selector = L1_PRICE_SELECTOR
                selected_mrp_selector = L1_MRP_SELECTOR
                selected_link_selector = L1_LINK_SELECTOR
            elif layout2_cards:
                cards_to_process = layout2_cards[:MAX_RESULTS]
                selected_name_selector = L2_NAME_SELECTOR
                selected_quantity_selector = L2_QUANTITY_SELECTOR
                selected_price_selector = L2_PRICE_SELECTOR
                selected_mrp_selector = L2_MRP_SELECTOR
                selected_link_selector = L2_LINK_SELECTOR
            else:
                cards_to_process = []

            results = []
            for i, card in enumerate(cards_to_process, 1):
                name = card.select_one(selected_name_selector)
                quantity = card.select_one(selected_quantity_selector)
                price = card.select_one(selected_price_selector)
                mrp = card.select_one(selected_mrp_selector)
                link_element = card.select_one(selected_link_selector)

                name_text = name.text.strip() if name else 'Name not found'
                quantity_text = quantity.text.strip() if quantity else 'Quantity not found'
                raw_price_text = price.text.strip() if price else 'Price not found'
                mrp_text = mrp.text.strip() if mrp else 'MRP not found'
                product_link = f"https://www.1mg.com{link_element['href']}" if link_element and link_element.get('href') else "Link not found"

                # Extract numeric price using regex
                price_match = re.search(r'₹\s*\d+\.?\d*', raw_price_text)
                price_text = price_match.group(0) if price_match else "Price not found"

                results.append({
                    'number': i,
                    'medicine': name_text,
                    'quantity': quantity_text,
                    'price': price_text,
                    'link': product_link
                })
            return results
        except Exception as e:
            logging.error(f"Error in scrape_1mg: {str(e)}")
            return []
        finally:
            if driver:
                driver.quit()

    # --- Execute Scraping for All Websites in Parallel ---
    formatted_term = search_term.replace(' ', '%20')
    
    # Use ThreadPoolExecutor to run scrapers in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all scraping tasks
        apollo_future = executor.submit(scrape_apollo, formatted_term)
        netmeds_future = executor.submit(scrape_netmeds, formatted_term)
        one_mg_future = executor.submit(scrape_1mg, formatted_term)
        
        # Get results as they complete
        apollo_results = apollo_future.result()
        netmeds_results = netmeds_future.result()
        one_mg_results = one_mg_future.result()

    # --- Return Results as Dictionary ---
    return {
        "Apollo Pharmacy": apollo_results,
        "Netmeds": netmeds_results,
        "1mg": one_mg_results
    }