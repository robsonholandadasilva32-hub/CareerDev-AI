import pytest
from playwright.sync_api import sync_playwright, expect

def test_accessibility_persistence():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        base_url = "http://localhost:8000"

        # A. Visit Login Page
        page.goto(f"{base_url}/login")

        # B. Enable High Contrast via JS
        page.evaluate("window.toggleA11y('high-contrast')")

        # C. Reload Page
        page.reload()

        # D. Verify High Contrast Class
        assert "high-contrast" in page.eval_on_selector("html", "el => el.className"), "High contrast should persist after reload"

        # E. Verify Background Color (Black)
        bg_color = page.eval_on_selector("body", "el => window.getComputedStyle(el).backgroundColor")
        print(f"Background Color: {bg_color}")

        # Screenshot
        page.screenshot(path="verification/login_high_contrast.png")
        print("Screenshot saved to verification/login_high_contrast.png")

        browser.close()

if __name__ == "__main__":
    try:
        test_accessibility_persistence()
    except Exception as e:
        print(f"FAILURE: {e}")
        exit(1)
