# launch_cloud.py (Retry Until Verified Online)
import json
import os
import time
import urllib.request
from typing import Any, cast
from playwright.sync_api import sync_playwright

NOTEBOOK_URL = "https://colab.research.google.com/drive/1mV3Du5Dwrywly-5I-l5eQCfnC_g6rG4X"
HEALTH_CHECK_URL = "https://atlas-ai-workspace.loca.lt/api/agents"
MAX_ATTEMPTS = 3


def check_is_online() -> bool:
    """Pings the permanent web app to confirm it is actually running"""
    try:
        req = urllib.request.Request(
            HEALTH_CHECK_URL, headers={"Bypass-Tunnel-Reminder": "true"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def format_cookie(c: dict) -> dict[str, Any]:
    cookie: dict[str, Any] = {
        "name": c["name"],
        "value": c["value"],
        "domain": c["domain"],
        "path": c.get("path", "/"),
        "secure": c.get("secure", True),
        "httpOnly": c.get("httpOnly", False),
    }
    if "sameSite" in c:
        s = c["sameSite"]
        if s in ["Strict", "Lax", "None"]:
            cookie["sameSite"] = s
        elif s == "no_restriction":
            cookie["sameSite"] = "None"
        elif s == "lax":
            cookie["sameSite"] = "Lax"
        elif s == "strict":
            cookie["sameSite"] = "Strict"
    return cookie


def attempt_launch(attempt: int) -> bool:
    print(f"\n🚀 [Attempt {attempt}/{MAX_ATTEMPTS}] Launching Google Colab...")

    with open("cookies.json", "r") as f:
        raw_cookies = json.load(f)

    cookies = [format_cookie(c) for c in raw_cookies]

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cast(Any, cookies))

        page = context.new_page()
        page.goto(NOTEBOOK_URL, timeout=90000)
        page.wait_for_load_state("networkidle")
        time.sleep(5)

        print("⚡ Triggering 'Run All' cells (Control+F9)...")
        page.keyboard.press("Control+F9")
        time.sleep(3)

        # Bypass 'Run anyway' dialog if present
        try:
            run_btn = page.locator(
                "paper-button:has-text('Run anyway'), paper-button:has-text('Yes')"
            )
            if run_btn.is_visible(timeout=5000):
                run_btn.click()
                print("   [✔] Bypassed 'Run anyway' modal.")
        except Exception:
            pass

        print("⏳ Polling health check for launch confirmation...")
        # Poll health check every 5s for up to 60s
        for _ in range(12):
            time.sleep(5)
            if check_is_online():
                print(
                    "\n🎉 [LAUNCH CONFIRMED] Atlas AI is fully online and responsive!"
                )
                browser.close()
                return True

        browser.close()
        print("⚠️ Health check timed out for this attempt.")
        return False


def main():
    if check_is_online():
        print("✔ Atlas is already online! No launch needed.")
        return

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt_launch(attempt):
            return
        print(f"🔄 Retrying in 10 seconds...")
        time.sleep(10)

    print("❌ Failed to confirm launch after max retries.")


if __name__ == "__main__":
    main()
