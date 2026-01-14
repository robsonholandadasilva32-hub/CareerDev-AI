from playwright.sync_api import sync_playwright
import time

def verify_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Verify Login Page
        try:
            print("Navigating to Login Page...")
            page.goto("http://localhost:8000/login")
            # Wait for the new section to appear
            page.wait_for_selector(".accessibility-showcase", timeout=5000)

            # Scroll to it
            element = page.locator(".accessibility-showcase")
            element.scroll_into_view_if_needed()

            # Take screenshot
            page.screenshot(path="verification/verification.png", full_page=True)
            print("Login Page screenshot saved as verification.png.")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error.png")

        browser.close()

if __name__ == "__main__":
    verify_ui()
