# launch_cloud.py (Type Safe for Pylance)
import json
import os
import time
from typing import Any, cast
from playwright.sync_api import sync_playwright

NOTEBOOK_URL = "https://colab.research.google.com/drive/1mV3Du5Dwrywly-5I-l5eQCfnC_g6rG4X"
COOKIE_FILE = "cookies.json"


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


def main():
    print("🚀 [Cloud Runner] Starting headless launch of Google Colab...")

    if not os.path.exists(COOKIE_FILE):
        print("❌ Error: cookies.json not found in workspace.")
        return

    with open(COOKIE_FILE, "r") as f:
        raw_cookies = json.load(f)

    cookies = [format_cookie(c) for c in raw_cookies]

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()

        # cast to satisfy Pylance
        context.add_cookies(cast(Any, cookies))

        page = context.new_page()
        page.goto(NOTEBOOK_URL, timeout=90000)
        page.wait_for_load_state("networkidle")
        time.sleep(5)

        print("⚡ Triggering 'Run All' cells (Control+F9)...")
        page.keyboard.press("Control+F9")
        time.sleep(3)

        # Handle 'Run anyway' confirmation dialog if it appears
        try:
            run_btn = page.locator(
                "paper-button:has-text('Run anyway'), paper-button:has-text('Yes')"
            )
            if run_btn.is_visible(timeout=5000):
                run_btn.click()
                print("   [✔] Bypassed 'Run anyway' prompt.")
        except Exception:
            pass

        print("⏳ Waiting 45 seconds for GPU container and model to boot...")
        time.sleep(45)

        print("🎉 Colab execution successfully triggered!")
        browser.close()


if __name__ == "__main__":
    main()
