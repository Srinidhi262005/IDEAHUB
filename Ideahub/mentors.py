# Ideahub/mentors.py
# ----------------------------------------------------
# AUTO LOAD REAL JITS FACULTY INTO DATABASE (CLEAN)
# ----------------------------------------------------

import time
import requests
from bs4 import BeautifulSoup

from flask import current_app
from Ideahub.extensions import db
from Ideahub.models import Mentor

# ----------------------------------------------------
# OFFICIAL JITS FACULTY PAGES (ONLY REAL SOURCES)
# ----------------------------------------------------
FACULTY_PAGES = {
    "https://jits.ac.in/cse_faculty-profiles/": "CSE",
    "https://jits.ac.in/cse-ai-ml-faculty/": "CSE AI & ML",
    "https://jits.ac.in/it-faculty/": "IT",
    "https://jits.ac.in/ece-faculty-profiles/": "ECE",
    "https://jits.ac.in/eee-faculty-profiles/": "EEE",
    "https://jits.ac.in/mechanical-engineering-faculty/": "MECHANICAL",
    "https://jits.ac.in/civil-engineering-faculty/": "CIVIL",
    "https://jits.ac.in/hs-faculty/": "H&S"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ----------------------------------------------------
# SCRAPE FACULTY FROM ONE PAGE
# ----------------------------------------------------
def scrape_page(url, department):
    mentors = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # JITS faculty name patterns
        name_tags = soup.select(
            "h3, h4, strong, .faculty-name, .staff-name"
        )

        for tag in name_tags:
            name = tag.get_text(strip=True)

            if not name:
                continue

            # Filter garbage text
            if len(name) > 120:
                continue

            if not any(x in name for x in ["Dr.", "Mr.", "Ms.", "Mrs.", "Prof."]):
                continue

            mentors.append({
                "name": name[:150],
                "department": department,
                "email": None,
                "qualification": None
            })

    except Exception as e:
        print(f"❌ Failed to scrape {url} -> {e}")

    return mentors


# ----------------------------------------------------
# SCRAPE ALL DEPARTMENTS
# ----------------------------------------------------
def scrape_all_faculty():
    all_mentors = []

    for url, dept in FACULTY_PAGES.items():
        print(f"📥 Scraping {dept} faculty...")
        data = scrape_page(url, dept)
        all_mentors.extend(data)
        time.sleep(1)

    # Remove duplicates by name
    unique = {m["name"]: m for m in all_mentors}
    return list(unique.values())


# ----------------------------------------------------
# AUTO UPDATE DATABASE (RUN ONCE)
# ----------------------------------------------------
def auto_update_mentors():
    """
    Loads real JITS faculty into Mentor table.
    ⚠️ Run ONLY ONCE, then comment it.
    """

    with current_app.app_context():
        print("🔄 Loading JITS faculty into database...")

        scraped = scrape_all_faculty()
        added = 0

        for data in scraped:
            exists = Mentor.query.filter_by(name=data["name"]).first()
            if exists:
                continue

            mentor = Mentor(
                name=data["name"],
                department=data["department"],
                email=data.get("email"),
                qualification=data.get("qualification")
            )

            db.session.add(mentor)
            added += 1

        db.session.commit()
        print(f"✅ Added {added} faculty members to database")





