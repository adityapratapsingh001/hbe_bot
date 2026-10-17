"""Verify renamed and reordered section tabs using offline markup."""

from playwright.sync_api import sync_playwright
from test_runner import discover_sections, section_tab

expected = ['Technical', 'Aptitude', 'English Language', 'Coding']
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    for tag in ('a', 'input'):
        controls = []
        for index, name in enumerate(expected):
            click = f"document.body.dataset.section='{index}'"
            if tag == 'a':
                controls.append(f'<a class="section_change" onclick="{click}"><span>{name}</span></a>')
            else:
                controls.append(f'<input type="button" value="{name}" onclick="{click}">')
        container = 'section' if tag == 'a' else 'tabs'
        page.set_content(
            '<h3>Technical</h3><a class="section_change" style="display:none">Verbal</a>'
            + f'<div id="{container}">' + ''.join(controls) + '</div>'
        )
        assert discover_sections(page) == expected
        for index, name in enumerate(expected):
            section_tab(page, name).click()
            assert page.locator('body').get_attribute('data-section') == str(index)
    browser.close()
print('PASS: Technical -> Aptitude -> English Language -> Coding, nested labels, hidden old tabs, input tabs')
