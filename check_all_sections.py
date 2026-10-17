"""Offline browser checks; no API calls or real test submissions."""

import ast
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_runner import discover_sections, find_test_surface, run_all_sections, section_tab


def main():
    for name in ("open_test.py", "open_test_fixed.py", "test_runner.py"):
        ast.parse(Path(name).read_text(encoding="utf-8"))
    tree = ast.parse(Path("open_test_fixed.py").read_text(encoding="utf-8"))
    definitions = [node for node in tree.body if isinstance(
        node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign)
    )]
    namespace = {}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "offline", "exec"), namespace)
    fixture = """
    <h3>English Language</h3><div id="tabs"></div><div id="total"></div>
    <div id="question"><div><b id="marker"></b></div><div id="content"></div></div>
    <div>Question Palette:</div><div id="question_buttons"></div>
    <a class="button savenext" onclick="save()">Save &amp; Next</a>
    <script>
    const names=['English Language','Quant & Reasoning','Technical','Coding'];
    const counts=[12,2,2,2], starts=[1,13,15,17];
    let section=0, q=1, submits=0, saves=0;
    let answers={'1':'b','2':'c'};
    function draw() {
      const globalQ=starts[section]+q-1;
      tabs.innerHTML=names.map((n,i)=> i===0
        ? `<input type="button" value="English Language" onclick="section=${i};q=1;draw()">`
        : `<button onclick="section=${i};q=1;draw()"><span>${n}</span></button>`).join('');
      total.textContent='Total Questions : '+counts[section];
      marker.textContent='Question No: '+q;
      const image=section===2 && q===1 ? '<svg width="30" height="30"><circle r="10" cx="15" cy="15"/></svg>' : '';
      content.innerHTML=`<div id="qno_${globalQ}">`+'Which option is correct?'+image+'<table>'+['a','b','c','d'].map(a=>`<tr><td><input type="radio" name="radio_${globalQ}" value="${a}" ${answers[globalQ]===a?'checked':''}></td><td>Choice ${a}</td></tr>`).join('')+'</table></div>';
      question_buttons.innerHTML='<div class="allsection" style="display:block">'+Array.from({length:counts[section]},(_,i)=>`<button class="buttonslist" data-qno="${starts[section]+i}" onclick="q=${i+1};draw()"><span>${i+1}</span></button>`).join('')+'</div>';
    }
    function save(){
      const radio=document.querySelector('input:checked');
      const globalQ=starts[section]+q-1;
      if(radio) answers[globalQ]=radio.value;
      saves++;
      if(q<counts[section]) q++; else {section=(section+1)%4;q=1;}
      draw();
    }
    draw();
    </script>
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        home = context.new_page()
        home.set_content('<h1>Login homepage</h1>')
        page = context.new_page()
        page.set_content(fixture)
        assert find_test_surface(home) == page
        assert discover_sections(page) == ['English Language', 'Quant & Reasoning', 'Technical', 'Coding']
        assert section_tab(page, 'English Language').get_attribute('type') == 'button'
        calls = []
        def ask(question, options, passage):
            calls.append(question)
            return "A"
        assert run_all_sections(
            home, namespace['get_question_number'], namespace['extract_question'], ask,
            namespace['select_answer'], namespace['click_save_next'], input_fn=lambda _: "D",
        )
        result = page.evaluate("({answers,saves,submits})")
        assert len(result['answers']) == 18
        assert result['answers']['1'] == 'b' and result['answers']['2'] == 'c'
        assert result['answers']['15'] == 'd'
        assert len(calls) == 15
        assert result['submits'] == 0
        # A missing section must not be reported as complete.
        page.set_content('<div>No sections loaded</div>')
        assert not run_all_sections(
            page, namespace['get_question_number'], namespace['extract_question'], ask,
            namespace['select_answer'], namespace['click_save_next'], input_fn=lambda _: "stop",
        )
        # The test can also be hosted inside a frame rather than the parent page.
        page.set_content('<iframe></iframe>')
        frame = page.frames[1]
        frame.set_content(fixture)
        assert find_test_surface(home) == frame
        section_tab(frame, 'Technical').click()
        assert frame.locator('#total').inner_text() == 'Total Questions : 2'
        # Missing tabs can be fixed in the same browser, then retried.
        frame.set_content('<div>Question No: 1</div><input name="radio_1" type="radio">')
        attempts = []
        def stop_after_pause(message):
            attempts.append(message)
            return 'stop'
        assert not run_all_sections(
            home, namespace['get_question_number'], namespace['extract_question'], ask,
            namespace['select_answer'], namespace['click_save_next'], input_fn=stop_after_pause,
        )
        assert len(attempts) == 1
        browser.close()
    print('PASS: popup detection, iframe detection, input tabs, duplicate headings, nested labels, pause on missing tabs, plus 18 questions across four sections')


if __name__ == '__main__':
    main()
