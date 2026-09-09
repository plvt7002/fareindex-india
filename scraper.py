import asyncio
import random
import re
import sqlite3
import time
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

def upgrade_db_schema():
    """Safely creates the table and adds new columns if they do not exist."""
    conn = sqlite3.connect("airfare.db")
    cursor = conn.cursor()
    
    # Create the base table if this is a fresh setup
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flight_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT,
            destination TEXT,
            airline TEXT,
            duration TEXT,
            stops TEXT,
            price TEXT,
            scraped_at TIMESTAMP,
            departure_time TEXT,
            arrival_time TEXT,
            travel_date TEXT,
            travel_class TEXT,
            source TEXT,
            seats_left TEXT
        )
    """)
    
    # Check existing columns and alter table if running on an older schema
    cursor.execute("PRAGMA table_info(flight_prices)")
    existing_columns = [info[1] for info in cursor.fetchall()]
    
    new_columns = [
        ("departure_time", "TEXT"),
        ("arrival_time", "TEXT"),
        ("travel_date", "TEXT"),
        ("travel_class", "TEXT"),
        ("source", "TEXT"),
        ("seats_left", "TEXT")
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE flight_prices ADD COLUMN {col_name} {col_type}")
            print(f"Database updated: Added column '{col_name}'")
            
    conn.commit()
    conn.close()

def save_to_database(origin, destination, travel_date, travel_class, source, flights):
    """Insert the scraped flight data into SQLite."""
    if not flights:
        print(f"⚠️ No flights to save for {origin} -> {destination}")
        return
        
    conn = sqlite3.connect("airfare.db")
    cursor = conn.cursor()
    current_time = datetime.now()
    
    for flight in flights:
        cursor.execute("""
            INSERT INTO flight_prices (
                origin, destination, airline, duration, stops, price, scraped_at,
                departure_time, arrival_time, travel_date, travel_class, source, seats_left
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            origin,
            destination,
            flight.get('airline'), 
            flight.get('duration'), 
            flight.get('stops'), 
            flight.get('price'), 
            current_time,
            flight.get('departure_time'),
            flight.get('arrival_time'),
            travel_date,
            travel_class,
            source,
            flight.get('seats_left')
        ))
    
    conn.commit()
    conn.close()
    print(f"✅ {len(flights)} flights saved for {origin} -> {destination}")

async def scrape_google_flights(origin: str, destination: str, date: str):
    async with async_playwright() as p:
        # Launch browser with anti-detection flags
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--window-size=1920,1080"
            ]
        )
        
        # Emulate Mac desktop environment
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-IN",
            timezone_id="Asia/Kolkata"
        )
        
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        # Explicitly request ONE WAY flight search in URL query
        query = f"one way flights from {origin} to {destination} on {date}"
        url = f"https://www.google.com/travel/flights?q={query.replace(' ', '+')}&curr=INR"
        
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(random.randint(2000, 3500))
        
        # Handle consent overlay if present
        try:
            consent_btn = page.locator('button:has-text("Accept all")')
            if await consent_btn.is_visible(timeout=2000):
                await consent_btn.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # 1. Establish and Verify Trip Type: One way
        trip_type_locator = page.locator(
            '[aria-label*="Trip type"], [role="combobox"]:has-text("Round trip"), [role="combobox"]:has-text("One way"), button:has-text("Round trip"), button:has-text("One way")'
        ).first
        if await trip_type_locator.is_visible(timeout=3000):
            trip_text = await trip_type_locator.inner_text()
            if "round trip" in trip_text.lower():
                await trip_type_locator.click()
                await page.wait_for_timeout(500)
                one_way_opt = page.locator('li:has-text("One way"), [role="option"]:has-text("One way")').first
                if await one_way_opt.is_visible(timeout=2000):
                    await one_way_opt.click()
                    await page.wait_for_timeout(2500)

        # Strict Verification: Verify page is in One way mode
        page_body_text = await page.inner_text("body")
        is_one_way = await page.locator(
            '[role="combobox"]:has-text("One way"), button:has-text("One way"), [aria-label*="One way"]'
        ).count() > 0

        if not is_one_way and "round trip" in page_body_text.lower() and "one way" not in page_body_text.lower():
            print(f"❌ Failed to verify ONE WAY trip type on Google Flights for {origin} -> {destination}.")
            await browser.close()
            return []

        # 2. Verify Cabin: Economy
        is_economy = await page.locator(
            '[role="combobox"]:has-text("Economy"), button:has-text("Economy"), [aria-label*="Economy"]'
        ).count() > 0
        if not is_economy and "business" in page_body_text.lower() and "economy" not in page_body_text.lower():
            print(f"❌ Failed to verify ECONOMY cabin class for {origin} -> {destination}.")
            await browser.close()
            return []

        # Wait for flight listing container to load
        try:
            await page.wait_for_selector("li.pIav2d", timeout=30000)
        except Exception:
            print(f"❌ Failed to locate flight cards for {origin} -> {destination}. Check DOM selectors or CAPTCHA.")
            await browser.close()
            return []

        flights = []
        flight_cards = await page.query_selector_all("li.pIav2d")
        
        for card in flight_cards:
            try:
                raw_text = await card.inner_text()
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                
                # Reject card if it states round trip
                if any("round trip" in line.lower() for line in lines):
                    continue

                # Verify card contains valid fare
                price_line = next((line for line in lines if '₹' in line), None)
                if not price_line or len(lines) < 4:
                    continue

                seats_info = next((line for line in lines if 'seat' in line.lower() or 'left' in line.lower()), "Available")
                stops_info = next((line for line in lines if 'stop' in line.lower() or 'nonstop' in line.lower() or 'non-stop' in line.lower()), "Unknown")

                if len(lines) >= 5 and lines[1] in ("–", "-", "—"):
                    dep_time = lines[0]
                    arr_time = lines[2]
                    airline = lines[3]
                    duration = lines[4]
                elif len(lines) >= 4:
                    dep_time = lines[0]
                    arr_time = lines[1]
                    airline = lines[2]
                    duration = lines[3]
                else:
                    dep_time = None
                    arr_time = None
                    airline = "Unknown"
                    duration = None

                flight_data = {
                    "departure_time": dep_time,
                    "arrival_time": arr_time,
                    "airline": airline,
                    "duration": duration,
                    "stops": stops_info,
                    "price": price_line,
                    "seats_left": seats_info,
                }
                flights.append(flight_data)
            except Exception:
                continue

        await browser.close()
        return flights

if __name__ == "__main__":
    # Ensure database schema is ready
    upgrade_db_schema()
    
    # Configure scrape targets
    routes_to_scrape = [
        {"origin": "HYD", "destination": "DEL"},
        {"origin": "HYD", "destination": "GOI"}
    ]
    
    target_date = "2026-10-15"
    travel_class = "Economy"
    source = "Google Flights"
    
    for route in routes_to_scrape:
        origin = route["origin"]
        destination = route["destination"]
        
        print(f"\n🚀 Running scraper for {origin} -> {destination} ({target_date})...")
        results = asyncio.run(scrape_google_flights(origin, destination, target_date))
        
        save_to_database(origin, destination, target_date, travel_class, source, results)
        
        # 10-second delay between requests to avoid bot rate limits
        print("Cooling down for 10 seconds before next route...")
        time.sleep(10)
        
    print("\n🎉 Batch scraping job completed!")
