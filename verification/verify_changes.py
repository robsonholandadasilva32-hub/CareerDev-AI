from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to Terms of Use...")
        page.goto("http://localhost:8000/legal/terms")

        # 1. Verify Cookie Banner Logic
        print("Checking Cookie Banner...")
        banner = page.locator("#tech-cookie-banner")
        # Banner should appear after 500ms
        page.wait_for_timeout(1000)
        expect(banner).to_be_visible()

        # Verify Text
        expect(page.locator(".tech-body")).to_contain_text("We use cookies to ensure the integrity of your session")

        # Verify No Preferences Button
        expect(page.locator("button:has-text('Preferences')")).not_to_be_visible()

        # Click Acknowledge
        page.locator(".btn-accept").click()
        expect(banner).not_to_be_visible()

        # Verify Persistence (Reload)
        print("Reloading to check persistence...")
        page.reload()
        page.wait_for_timeout(1000) # Wait to ensure it DOES NOT appear
        expect(banner).not_to_be_visible()

        # Verify localStorage
        val = page.evaluate("localStorage.getItem('cookie_consent_accepted')")
        assert val == 'true', f"Expected localStorage cookie_consent_accepted to be 'true', got {val}"

        # 2. Verify Terms Text (English)
        print("Checking Terms Text...")
        # "To provide..."
        expect(page.locator("body")).to_contain_text("To provide truthful information")
        expect(page.locator("body")).to_contain_text("Not to share your access credentials")

        # 3. Verify Privacy Link Target
        print("Checking Privacy Link Target...")
        privacy_links = page.get_by_role("link", name="Privacy Policy").all()
        print(f"Found {len(privacy_links)} Privacy Policy links.")
        for i, link in enumerate(privacy_links):
            target = link.get_attribute("target")
            print(f"Link {i}: target='{target}'")
            assert target != "_blank", f"Privacy Policy link {i} has target='{target}', expected None or not '_blank'"

        # Take screenshot
        page.screenshot(path="verification/verification.png", full_page=True)
        print("Verification complete. Screenshot saved.")

        browser.close()

if __name__ == "__main__":
    run()
