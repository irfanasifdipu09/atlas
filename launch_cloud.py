# launch_cloud.py (Ultra-Reliable Colab Trigger)
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
    print(
        "🚀 Launching Google Colab headlessly on T4 GPU...",
        flush=True,
    )

    if not os.path.exists(COOKIE_FILE):
        print("❌ Error: cookies.json not found.", flush=True)
        return

    with open(COOKIE_FILE, "r") as f:
        raw_cookies = json.load(f)

    cookies = [format_cookie(c) for c in raw_cookies]

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cast(Any, cookies))

        page = context.new_page()
        page.goto(NOTEBOOK_URL, timeout=90000)
        page.wait_for_load_state("networkidle")
        time.sleep(6)

        print("⚡ Triggering 'Run All' in Colab...", flush=True)
        # 1. Trigger Run All shortcut
        page.keyboard.press("Control+F9")
        time.sleep(3)

        # 2. Click any modal dialog buttons ("Run anyway", "Connect to hosted runtime", "Yes", "OK")
        dialog_selectors = [
            "md-text-button:has-text('Run anyway')",
            "mwc-button:has-text('Run anyway')",
            "paper-button:has-text('Run anyway')",
            "button:has-text('Run anyway')",
            "md-text-button:has-text('Yes')",
            "paper-button:has-text('Yes')",
            "md-text-button:has-text('Connect')",
        ]
        for sel in dialog_selectors:
            try:
                btn = page.locator(sel)
                if btn.is_visible(timeout=1000):
                    btn.click()
                    print(f"   [✔] Clicked confirmation: {sel}", flush=True)
            except Exception:
                pass

        print(
            "🎉 Colab execution successfully engaged! Exiting cloud launcher...",
            flush=True,
        )
        time.sleep(10)
        browser.close()


if __name__ == "__main__":
    main()
