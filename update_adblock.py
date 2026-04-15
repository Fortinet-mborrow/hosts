"""
update_adblock.py

Checks if the StevenBlack hosts file has been updated since the last run.
If it has, strips all '0.0.0.0 ' prefixes from each line and saves the
result to 'adblock_master_updated'.

Designed to run as a GitHub Actions workflow or any CI/CD pipeline.
State (last-seen date) is stored in '.last_hosts_date' alongside this script.
"""

import re
import sys
import urllib.request
from pathlib import Path

HOSTS_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
OUTPUT_FILE = Path("adblock_master_updated")
STATE_FILE = Path(".last_hosts_date")

DATE_PATTERN = re.compile(r"^# Date:\s+(.+)$", re.MULTILINE)


def fetch_hosts() -> str:
    """Download the remote hosts file and return its content as a string."""
    print(f"Fetching: {HOSTS_URL}")
    with urllib.request.urlopen(HOSTS_URL, timeout=30) as response:
        return response.read().decode("utf-8")


def extract_date(content: str) -> str | None:
    """Pull the '# Date: ...' value out of the hosts file header."""
    match = DATE_PATTERN.search(content)
    return match.group(1).strip() if match else None


def read_last_date() -> str | None:
    """Return the date string saved from the previous run, or None."""
    if STATE_FILE.exists():
        return STATE_FILE.read_text(encoding="utf-8").strip() or None
    return None


def save_last_date(date_str: str) -> None:
    """Persist the current date string so we can compare on the next run."""
    STATE_FILE.write_text(date_str, encoding="utf-8")
    print(f"State saved to '{STATE_FILE}'.")


def process_hosts(content: str) -> str:
    """
    Remove the '0.0.0.0 ' prefix (and any surrounding whitespace)
    from every line that starts with it.

    Lines that are comments, blank, or do not begin with '0.0.0.0'
    are left exactly as-is.
    """
    output_lines: list[str] = []
    for line in content.splitlines(keepends=True):
        # Strip the leading '0.0.0.0' and the single trailing space after it.
        # Using lstrip on the remainder catches any extra whitespace edge cases.
        if line.startswith("0.0.0.0 "):
            line = line[len("0.0.0.0 "):]
    
        output_lines.append(line)
    return "".join(output_lines)


def main() -> None:
    # 1. Download the file.
    try:
        content = fetch_hosts()
    except Exception as exc:
        print(f"ERROR: Could not fetch hosts file — {exc}", file=sys.stderr)
        sys.exit(1)

    # 2. Extract the embedded date.
    current_date = extract_date(content)
    if current_date is None:
        print(
            "WARNING: Could not find a '# Date:' header in the hosts file. "
            "Proceeding with update anyway.",
            file=sys.stderr,
        )

    print(f"Remote file date : {current_date or '(unknown)'}")

    # 3. Compare with the last-seen date.
    last_date = read_last_date()
    print(f"Last processed   : {last_date or '(never)'}")

    if current_date and current_date == last_date:
        print("No update detected — output file not changed.")
        return

    # 4. Process and write output.
    print("Update detected — processing hosts file …")
    processed = process_hosts(content)

    OUTPUT_FILE.write_text(processed, encoding="utf-8")
    print(f"Output written to '{OUTPUT_FILE}' ({OUTPUT_FILE.stat().st_size:,} bytes).")

    # 5. Persist state.
    if current_date:
        save_last_date(current_date)


if __name__ == "__main__":
    main()
