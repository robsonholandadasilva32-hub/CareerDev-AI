from playwright.sync_api import sync_playwright

def verify_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://localhost:8000/login")
            # Wait for content
            page.wait_for_selector(".login-container")

            # Screenshot
            page.screenshot(path="verification/login_page.png")
            print("Screenshot taken.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_login()
