from playwright.sync_api import sync_playwright

def verify_routes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Verify Public Accessibility Page (Unauthenticated)
        print("Navigating to public accessibility page...")
        page.goto("http://localhost:8000/accessibility")
        page.wait_for_selector(".public-header h1")
        title = page.inner_text(".public-header h1")
        print(f"Page title: {title}")
        assert "Universal Access" in title
        page.screenshot(path="verification/public_accessibility.png")
        print("Screenshot saved: verification/public_accessibility.png")

        # 2. Verify Public Legal Pages
        print("Navigating to Terms...")
        page.goto("http://localhost:8000/legal/terms")

        # Use a more generic selector or wait for text content
        # The previous attempt failed because it didn't find "h1" with the text or timing issue
        # Let's inspect the page content to be safe
        page.wait_for_selector(".card h1")
        h1_text = page.inner_text(".card h1")
        print(f"Terms H1: {h1_text}")
        assert "Terms of Use" in h1_text

        page.screenshot(path="verification/public_terms.png")
        print("Screenshot saved: verification/public_terms.png")

        print("Navigating to Privacy...")
        page.goto("http://localhost:8000/legal/privacy")
        page.wait_for_selector(".card h1")
        privacy_text = page.inner_text(".card h1")
        print(f"Privacy H1: {privacy_text}")
        assert "Privacy Policy" in privacy_text
        page.screenshot(path="verification/public_privacy.png")
        print("Screenshot saved: verification/public_privacy.png")

        # 3. Verify Security Redirect (Unauthenticated)
        print("Navigating to Security (should redirect)...")
        page.goto("http://localhost:8000/security")
        # Should end up at login
        assert "/login" in page.url
        page.screenshot(path="verification/security_redirect.png")
        print("Screenshot saved: verification/security_redirect.png")

        # 4. Verify Login Page Accessibility Link
        print("Checking Login Page footer...")
        page.goto("http://localhost:8000/login")

        # Use get_by_label which is robust
        accessibility_link = page.get_by_label("Accessibility Options")
        assert accessibility_link.is_visible()

        page.screenshot(path="verification/login_footer.png")
        print("Screenshot saved: verification/login_footer.png")

        browser.close()

if __name__ == "__main__":
    verify_routes()
