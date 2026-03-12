"""Pagination: auto-iterate vs manual page control."""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

# ── Auto-pagination (iterate everything) ────────────────────
print("=== Auto-pagination ===")
count = 0
for app in client.applications.list(entry_year=2026, page_size=50):
    count += 1
    if count <= 3:
        print(f"  {app['first_name']} {app['last_name']}")
    elif count == 4:
        print("  ...")
print(f"Total iterated: {count}")

# ── Manual page control ─────────────────────────────────────
print("\n=== Manual pagination ===")
page_num = 1
while True:
    page = client.applications.list_page(
        entry_year=2026, page=page_num, page_size=10
    )
    print(f"Page {page_num}: {len(page)} results (of {page.count} total)")

    for app in page:
        print(f"  {app['first_name']} {app['last_name']}")

    if not page.next:
        break
    page_num += 1
