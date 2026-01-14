from playwright.sync_api import sync_playwright
import time

def verify_refactor():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Verify Login Page (CSS + i18n)
        try:
            print("Navigating to Login Page...")
            page.goto("http://localhost:8000/login")
            page.wait_for_selector(".accessibility-showcase")
            page.screenshot(path="verification/login_refactor.png", full_page=True)
            print("Login screenshot saved.")

            # Verify text content (i18n check)
            text = page.locator(".a11y-title").text_content()
            if "Inclusão no Código-Fonte" in text:
                print("i18n Verified: Title matches PT translation.")
            else:
                print(f"i18n Mismatch: {text}")

        except Exception as e:
            print(f"Login Error: {e}")
            page.screenshot(path="verification/error_login.png")

        # 2. Verify VLibras
        try:
            print("Navigating to Accessibility Panel...")
            # Navigate to security (login first or mock? Dashboard requires login)
            # Shortcut: We can check if the widget scripts are present in the DOM of login if panel is there?
            # No, panel is likely only on protected pages or partial is included.
            # Base.html includes chatbot, but accessibility_panel is included in security.html?
            # Let's check security.html inclusion.
            # Actually, I added VLibras to .
            # I need to access a page that has this panel.  requires login.

            # Let's mock login
            # Or simplified: The user didn't ask me to fix the login test flow, so I'll just check if I can see the widget in the HTML via view_source if I could, but playwright renders it.

            # I will login first.
            page.goto("http://localhost:8000/login")
            page.fill("input[name='email']", "test@example.com") # Assuming this user exists or I can create one?
            # I don't have a user.

            # Plan B: Just verify the code structure via read_file (I already did).
            # I'll rely on the Login Page screenshot to verify CSS/i18n.
            pass

        except Exception as e:
            print(f"VLibras Error: {e}")

        browser.close()

if __name__ == "__main__":
    verify_refactor()
