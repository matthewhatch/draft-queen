"""Debug script to inspect Yahoo Sports page structure."""

import requests
from bs4 import BeautifulSoup
import json

url = "https://sports.yahoo.com/nfl/draft/"

# Fetch with browser headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    print("\n=== PAGE TITLE ===")
    print(soup.title.string if soup.title else "No title")
    
    print("\n=== ALL CLASSES IN PAGE (first 50) ===")
    classes = set()
    for tag in soup.find_all(True):
        if tag.get("class"):
            for cls in tag.get("class"):
                classes.add(cls)
    
    for cls in sorted(list(classes))[:50]:
        print(f"  .{cls}")
    
    print("\n=== LOOKING FOR PLAYER DATA ===")
    
    # Check for common structures
    tables = soup.find_all("table")
    print(f"Tables found: {len(tables)}")
    
    divs_with_player = soup.find_all("div", class_=lambda x: x and "player" in x.lower())
    print(f"Divs with 'player' in class: {len(divs_with_player)}")
    
    # Look for any table with prospect-like data
    if tables:
        print("\n=== FIRST TABLE STRUCTURE ===")
        first_table = tables[0]
        rows = first_table.find_all("tr")
        print(f"Rows: {len(rows)}")
        if rows:
            first_row = rows[0]
            cols = first_row.find_all(["th", "td"])
            print(f"Columns: {len(cols)}")
            print("First row content:")
            for i, col in enumerate(cols[:5]):
                print(f"  Col {i}: {col.get_text(strip=True)[:100]}")
            
            if len(rows) > 1:
                print("\nSecond row (sample data):")
                second_row = rows[1]
                cols = second_row.find_all(["th", "td"])
                for i, col in enumerate(cols[:5]):
                    print(f"  Col {i}: {col.get_text(strip=True)[:100]}")
    
    print("\n=== LOOKING FOR NAMES/POSITIONS ===")
    # Search for common position strings
    html_text = response.text
    positions = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]
    for pos in positions:
        count = html_text.count(f'"{pos}"') + html_text.count(f"'{pos}'") + html_text.count(f">{pos}<")
        if count > 0:
            print(f"  {pos}: {count} occurrences")
    
    print("\n=== PAGE LENGTH ===")
    print(f"Total HTML: {len(response.text)} bytes")
    print(f"Total text content: {len(soup.get_text())} bytes")
    
    # Check if it's dynamically loaded
    scripts = soup.find_all("script")
    print(f"\nScripts found: {len(scripts)}")
    
    # Look for JSON data
    for script in scripts:
        if script.string and ("prospect" in script.string.lower() or "draft" in script.string.lower()):
            print(f"\n=== FOUND RELEVANT SCRIPT ===")
            content = script.string[:500]
            print(content)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
