#!/usr/bin/env python3

import sys
import subprocess
import plistlib
from datetime import date, datetime
import json
from pathlib import Path
from calendar import monthrange

def calculate_age_detail(birthdate):
    """Return (years, months, days) since birthdate."""
    today = date.today()
    years = today.year - birthdate.year
    months = today.month - birthdate.month
    days = today.day - birthdate.day

    if days < 0:
        # Borrow days from previous month.
        months -= 1
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month != 1 else today.year - 1
        days += monthrange(prev_year, prev_month)[1]

    if months < 0:
        months += 12
        years -= 1

    return years, months, days

def time_until_next_birthday(birthdate):
    """Return (months, days) until the next birthday from today."""
    today = date.today()
    # Compute this year's birthday.
    next_bday = birthdate.replace(year=today.year)
    if next_bday < today:
        next_bday = birthdate.replace(year=today.year + 1)

    months = next_bday.month - today.month
    days = next_bday.day - today.day

    if days < 0:
        months -= 1
        prev_month = (today.month % 12) + 1
        prev_year = today.year if prev_month != 1 else today.year - 1
        days += monthrange(prev_year, prev_month)[1]

    if months < 0:
        months += 12

    return months, days

query = sys.argv[1] if len(sys.argv) > 1 else ""

# Spotlight search: only return AddressBook person contacts.
cmd = [
    "mdfind",
    "-onlyin",
    str(Path.home() / "Library/Application Support/AddressBook"),
    f'kMDItemDisplayName == "*{query}*"c && kMDItemContentTypeTree == "com.apple.addressbook.person"'
]
results = subprocess.run(cmd, capture_output=True, text=True)
paths = [line.strip() for line in results.stdout.splitlines() if line.strip()]

items = []

for path in paths:
    try:
        with open(path, "rb") as f:
            data = plistlib.load(f)
    except Exception:
        continue

    first = data.get("First", "")
    last = data.get("Last", "")

    # Skip placeholder contacts without a first or last name.
    if not first and not last:
        continue

    name = f"{first} {last}".strip()

    birthday = data.get("Birthday")
    subtitle = "No birthday set"
    if isinstance(birthday, datetime):
        birthday = birthday.date()
    if isinstance(birthday, date):
        years, months, days = calculate_age_detail(birthday)
        months_until, days_until = time_until_next_birthday(birthday)

        # Determine next birthday text.
        if months_until == 0 and days_until == 0:
            next_bday_text = "🎉 Today!"
        else:
            next_bday_text = f"Next birthday in {months_until}m {days_until}d"

        subtitle = (
            f"Born {birthday.strftime('%B %d, %Y')} "
            f"(Age: {years}y {months}m {days}d; {next_bday_text})"
        )

    item = {
        "title": name,
        "subtitle": subtitle,
        "arg": path,  # Used for ENTER action (open in Contacts.app).
        "uid": path,
        "text": {
            "copy": f"{name} — {subtitle}",
            "largetype": f"{name} — {subtitle}"
        }
    }
    items.append(item)

if not items:
    items = [{"title": "No matches", "subtitle": f"No contacts for '{query}'"}]

print(json.dumps({"items": items}))
