from playwright.sync_api import sync_playwright, TimeoutError
from datetime import datetime, timedelta
import re
import time
import json

# timeouts (ms)
NETWORK_IDLE_TIMEOUT = 15000
RESULTS_SELECTOR_TIMEOUT = 15000
POLL_ATTEMPTS = 5
POLL_INTERVAL = 1.0

def future_date_str(days_from_now=14):
    return (datetime.now() + timedelta(days=days_from_now)).strftime("%d-%m-%Y")

def text_or_none(locator):
    try:
        txt = locator.text_content(timeout=1000)
        return txt.strip() if txt else None
    except:
        return None

def extract_from_row(row):
    try:
        row_text = row.inner_text(timeout=2000) or ""
    except:
        row_text = ""

    airline = text_or_none(row.locator("p.h6").first) or text_or_none(row.locator("p.responsive-bold").first)
    flight_number = text_or_none(row.locator("p.mb-0.d-inline.d-lg-block").first) or text_or_none(row.locator("p:has-text('-')").first)
    times = re.findall(r"\b([0-2]?\d:[0-5]\d)\b", row_text)
    departure_time = times[0] if len(times) >= 1 else ""
    arrival_time = times[1] if len(times) >= 2 else ""

    price = ""
    m = re.search(r"₹\s*([0-9,]+(?:\.\d+)?)", row_text)
    if m:
        price = m.group(1).replace(",", "")
    else:
        m = re.search(r"(?:Rs\.|INR)\s*([0-9,]+(?:\.\d+)?)", row_text)
        if m:
            price = m.group(1).replace(",", "")

    if not flight_number:
        m = re.search(r"\b([A-Z0-9]{2,3}-\d{2,5})\b", row_text)
        if m:
            flight_number = m.group(1)

    if not airline:
        if flight_number:
            parts = row_text.split(flight_number)[0]
            m = re.search(r"([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*)\s*$", parts.strip())
            if m:
                airline = m.group(1).strip()
        if not airline:
            for name in ["Indigo", "Air India", "SpiceJet", "Vistara", "GoAir", "AirAsia", "Alliance Air"]:
                if name.lower() in row_text.lower():
                    airline = name
                    break

    return {
        "airline": airline or "",
        "flight_number": flight_number or "",
        "departure_time": departure_time or "",
        "arrival_time": arrival_time or "",
        "price": price or ""
    }

def run(playwright):
    origin_city = "Bangalore"
    destination_city = "Delhi"

    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.budgetticket.in", timeout=60000)

    # origin
    origin = page.locator("input[placeholder='Select Origin City']").first
    origin.wait_for(timeout=15000)
    origin.fill(origin_city)
    page.wait_for_selector(".angucomplete-row", timeout=10000)
    try:
        page.locator(".angucomplete-row", has_text=origin_city.upper()).first.click()
    except:
        page.locator(".angucomplete-row").first.click()

    # destination
    dest = page.locator("input[placeholder='Select Destination City']").first
    dest.wait_for(timeout=10000)
    dest.fill(destination_city)
    page.wait_for_selector(".angucomplete-row", timeout=10000)
    try:
        page.locator(".angucomplete-row", has_text=destination_city.upper()).first.click()
    except:
        page.locator(".angucomplete-row").first.click()

    # date
    date_str = future_date_str(14)
    date_selectors = [
        "input[name='journeydate']",
        "input[placeholder*='Date']",
        "input[placeholder*='Journey']",
        "input[type='date']",
        "input[id*='date']",
    ]
    for s in date_selectors:
        try:
            loc = page.locator(s).first
            if loc.count() and loc.is_visible():
                loc.fill(date_str)
                break
        except:
            continue

    # click Search
    search_btn = page.locator("input[type='submit'][value='Search']").first
    search_btn.wait_for(timeout=10000)
    search_btn.click()

    # record UTC search datetime
    search_datetime_utc = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    try:
        page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)
        print(f"networkidle reached (within {NETWORK_IDLE_TIMEOUT} ms).")
    except TimeoutError:
        print(f"networkidle timed out after {NETWORK_IDLE_TIMEOUT} ms, continuing to wait for result selector.")

    selector = "div[id^='Flight_']"
    rows = None
    try:
        page.wait_for_selector(selector, timeout=RESULTS_SELECTOR_TIMEOUT)
        rows = page.locator(selector)
        print(f"Found result rows via selector within {RESULTS_SELECTOR_TIMEOUT} ms.")
    except TimeoutError:
        print(f"Result selector did not appear within {RESULTS_SELECTOR_TIMEOUT} ms, polling for rows up to {POLL_ATTEMPTS * POLL_INTERVAL} seconds.")
        for attempt in range(POLL_ATTEMPTS):
            candidate = page.locator(selector)
            try:
                cnt = candidate.count()
            except Exception:
                cnt = 0
            if cnt and cnt > 0:
                rows = candidate
                print(f"Found {cnt} rows on poll attempt {attempt+1}.")
                break
            time.sleep(POLL_INTERVAL)
        if not rows:
            print("No flight rows found after polling. Exiting extraction step.")
            browser.close()
            return

    count = rows.count()
    print(f"\nTotal Flights Found: {count}\n{'-'*70}")
    flights = []
    for i in range(count):
        try:
            row = rows.nth(i)
            flight = extract_from_row(row)
            if any([flight["price"], flight["flight_number"], flight["airline"]]):
                flights.append(flight)
                print(f"{i+1}. {flight['airline']} ({flight['flight_number']})")
                print(f"   Departure: {flight['departure_time']} | Arrival: {flight['arrival_time']} | Price: ₹{flight['price']}")
                print("-" * 70)
        except Exception as e:
            print(f"Error extracting row {i+1}: {e}")
            continue

    output = {
        "searchdatetime": search_datetime_utc,
        "search": {
            "origin": origin_city,
            "destination": destination_city,
            "journey_date": date_str
        },
        "results": flights,
        "extracted_at": datetime.now().isoformat()
    }

    with open("flight_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Extracted {len(flights)} flights. Saved to flight_results.json successfully.\n")
    page.wait_for_timeout(500)
    browser.close()

with sync_playwright() as p:
    run(p)

