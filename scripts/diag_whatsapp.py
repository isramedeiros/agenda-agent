import os
import ssl
import urllib.request
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ics_url = os.environ.get("GOOGLE_CALENDAR_ICS_URL", "")
if not ics_url:
    raise SystemExit("Defina GOOGLE_CALENDAR_ICS_URL no ambiente antes de executar.")
with urllib.request.urlopen(ics_url, context=ctx, timeout=10) as resp:
    text = resp.read().decode("utf-8", errors="ignore").replace("\r\n ", "").replace("\n ", "")

blocks = text.split("BEGIN:VEVENT")[1:]
print("TOTAL_VEVENTS:", len(blocks))
nov_events = []
rrule_events = []
for b in blocks:
    eb = b.split("END:VEVENT")[0]
    if "STATUS:CANCELLED" in eb:
        continue
    s = re.search(r"SUMMARY(?:;[^:]*)?:(.+)", eb)
    dt = re.search(r"DTSTART(?:;[^:]*)?:(.+)", eb)
    rr = re.search(r"RRULE:(.+)", eb)
    summary = s.group(1).strip() if s else ""
    dtstart = dt.group(1).strip() if dt else ""
    if "202611" in dtstart or "202612" in dtstart:
        nov_events.append((dtstart, summary, rr.group(1).strip() if rr else ""))
    if rr and "UNTIL=" not in rr.group(1):
        rrule_events.append((dtstart, summary, rr.group(1).strip()))

print("NOV_DEC_2026_EVENTS:", len(nov_events))
for item in sorted(nov_events):
    print("  EVENT:", item)
print("ACTIVE_RRULE_EVENTS:", len(rrule_events))
for item in rrule_events[:15]:
    print("  RRULE:", item)
