"""Offline autofill check with a synthetic login form."""

import ast
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright
from browser_startup import autofill_login

for name in ('browser_startup.py', 'open_test.py', 'open_test_fixed.py'):
    ast.parse(Path(name).read_text(encoding='utf-8'))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.route('**/*', lambda route: route.fulfill(
        content_type='text/html', body='''<form>
        <input name="username" type="text"><input name="password" type="password">
        <button onclick="window.submitted=true;return false">Login</button></form>'''
    ))
    page.goto('https://www.hitbullseye.com/login')
    with patch('browser_startup.Path.read_text', return_value=
               '{"username":"dummy-user","password":"dummy-password"}'):
        assert autofill_login(page, timeout_seconds=1)
        assert page.locator('[name=username]').input_value() == 'dummy-user'
        assert page.locator('[name=password]').input_value() == 'dummy-password'
        assert not page.evaluate('Boolean(window.submitted)')
        page.goto('https://example.test/login')
        assert not autofill_login(page, timeout_seconds=1)
        assert page.locator('[name=password]').input_value() == ''
    browser.close()
print('PASS: autofill, domain restriction, no form submission, syntax')
