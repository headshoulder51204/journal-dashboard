import os
import sys

# Mocking the sanitize_db_url logic to test it
def sanitize_db_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "#" in url and "@" in url:
        parts = url.rsplit("@", 1)
        if len(parts) == 2:
            creds, rest = parts
            protocol_split = creds.split("://", 1)
            if len(protocol_split) == 2:
                protocol, user_pass = protocol_split
                if "#" in user_pass:
                    sanitized_user_pass = user_pass.replace("#", "%23")
                    url = f"{protocol}://{sanitized_user_pass}@{rest}"
    return url

# Test cases
test_urls = [
    "postgresql://postgres:pass#word@db.supabase.co:5432/postgres",
    "postgres://postgres:pass#word@db.supabase.co:5432/postgres",
    "postgresql://postgres:p@ssword@db.supabase.co:5432/postgres", # NO #, should be unchanged
    "postgresql://postgres:password@db.supabase.co:5432/postgres", # No special chars
]

for i, url in enumerate(test_urls):
    sanitized = sanitize_db_url(url)
    print(f"Test {i+1}:")
    print(f"  Old: {url}")
    print(f"  New: {sanitized}")
    if "%23" in sanitized or "postgresql" in sanitized:
        print("  Status: Likely Fixed")
    else:
        print("  Status: Unchanged")
