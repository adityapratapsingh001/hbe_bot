"""Open the login page without aborting the manual-login workflow."""

from playwright.sync_api import Error, TimeoutError
import json
from pathlib import Path
from urllib.parse import urlparse


def open_login_page(page, url):
    try:
        # Redirects and slow resources can delay DOMContentLoaded after the page
        # is already usable. Let the user complete login once navigation commits.
        page.goto(url, wait_until="commit", timeout=30000)
    except TimeoutError:
        print("[Browser] Initial navigation timed out; the browser remains open.")
        print(f"[Browser] Refresh or open {url} manually, then login and open the test.")
    except Error as error:
        if page.is_closed():
            raise
        print(f"[Browser] Initial navigation failed: {error}")
        print(f"[Browser] Open {url} manually, then login and open the test.")


def autofill_login(page, timeout_seconds=30):
    credentials = json.loads(
        Path(__file__).with_name("login_credentials.json").read_text(encoding="utf-8")
    )
    for _ in range(timeout_seconds):
        for candidate in page.context.pages:
            for frame in candidate.frames:
                host = urlparse(frame.url).hostname or ""
                if host != "hitbullseye.com" and not host.endswith(".hitbullseye.com"):
                    continue
                passwords = frame.locator("input[type='password']:visible")
                if passwords.count() != 1:
                    continue
                password = passwords.first
                form = password.locator("xpath=ancestor::form[1]")
                scope = form if form.count() else frame
                inputs = scope.locator(
                    "input[type='text']:visible, input[type='email']:visible, "
                    "input[type='tel']:visible, input[type='number']:visible, input:not([type]):visible"
                )
                indices = inputs.evaluate_all(r"""elements => elements.map((el, index) => ({
                    index, label: [el.name, el.id, el.placeholder, el.autocomplete].join(' ')
                })).filter(item => /user|login|student|roll|email/i.test(item.label))
                    .map(item => item.index)""")
                if len(indices) == 1:
                    username = inputs.nth(indices[0])
                elif inputs.count() == 1:
                    username = inputs.first
                else:
                    print("[Login] Could not identify one username field. Fill the form manually.")
                    return False
                username.fill(credentials["username"])
                password.fill(credentials["password"])
                print("[Login] Username and password filled. Click Login and open your mock test.")
                return True
        page.wait_for_timeout(1000)
    print("[Login] No login form found yet.")
    return False


def prepare_login(page):
    if not autofill_login(page):
        action = input("Open the login form, then press ENTER to auto-fill; type skip if already logged in: ")
        if action.strip().lower() != "skip":
            autofill_login(page)
