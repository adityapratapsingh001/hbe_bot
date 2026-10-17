"""Check section discovery on captured HTML without loading remote resources."""

import ast
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_runner import discover_sections, question_numbers, run_all_sections, section_tab


tree = ast.parse(Path('open_test_fixed.py').read_text(encoding='utf-8'))
namespace = {}
definitions = [node for node in tree.body if isinstance(
    node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign)
)]
exec(compile(ast.Module(body=definitions, type_ignores=[]), 'offline', 'exec'), namespace)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.route('**/*', lambda route: route.abort())
    html = Path('debug/navigation_2026-10-05_16-55-27_062414.html').read_text(encoding='utf-8')
    html = re.sub(r'<script\b[^>]*>.*?</script\s*>', '', html, flags=re.I | re.S)
    page.set_content(html, wait_until='domcontentloaded')
    expected = ['English Language', 'Quant & Reasoning', 'Technical', 'Coding']
    assert discover_sections(page) == expected
    for name in expected:
        assert section_tab(page, name).count() == 1
    assert question_numbers(page) == list(range(1, 41))
    assert namespace['get_question_number'](page) == 1
    passage, question, options = namespace['extract_question'](page, 1)
    assert 'address' in question and set(options) == set('ABCD')
    # Switch the saved DOM to Quant without executing the real site's handlers.
    page.evaluate("""() => {
        document.querySelectorAll('.allsection').forEach(el => el.style.display = 'none');
        document.querySelector('#sectionquestion_50792').style.display = 'block';
        document.querySelector('#total_questions_display').textContent = '80';
    }""")
    assert question_numbers(page) == list(range(41, 121))
    page.set_content('''
        <div id="section"><a class="section_change" onclick="void(0)">Coding</a></div>
        <div>Total Questions : 1</div><div>Question No: 1</div>
        <div id="question_buttons"><div class="allsection" style="display:block">
          <button class="buttonslist" data-qno="133">1</button>
        </div></div>
        <div id="qno_133" class="question_area"><textarea>Write a program</textarea></div>
    ''')
    assert namespace['get_question_number'](page) == 133
    calls = []
    def unexpected(*args):
        calls.append(args)
        raise AssertionError('Non-MCQ questions must not be sent to the A/B/C/D solver')
    assert not run_all_sections(
        page, namespace['get_question_number'], unexpected, unexpected,
        unexpected, unexpected, input_fn=lambda _: 'stop',
    )
    assert not calls
    browser.close()
print('PASS: current Cognizant sections, 40 English/80 Quant questions, extraction, explicit handling of non-MCQ coding')
