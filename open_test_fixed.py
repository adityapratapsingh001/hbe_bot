import re
import requests
from prompt_logging import prepare_prompt, save_prompt
from gpt_question import solve_question
from test_runner import run_all_sections
from browser_startup import open_login_page, prepare_login

from playwright.sync_api import sync_playwright

URL = "https://onlinetest.hitbullseye.com/online_load/hitbullseye_test.php"

GPT_URL = "http://localhost:3102/v1/generate"




def call_gpt(prompt):
    prompt = prepare_prompt(prompt)
    print("\n[GPT] Prompt length:", len(prompt))
    prompt_path = save_prompt(prompt)

    response = requests.post(
        GPT_URL,
        json={"prompt": prompt},
        timeout=120
    )

    print("[GPT] HTTP:", response.status_code)

    response_path = prompt_path.with_suffix('.response.txt')
    response_path.write_text(response.text, encoding='utf-8')
    print('[GPT] Response saved:', response_path)
    response.raise_for_status()

    data = response.json()

    if not data.get("success", True):
        raise RuntimeError(f"GPT API returned failure: {data}")

    return str(data.get("response", "")).strip()

def ask_gpt(question, options, passage=""):
    return solve_question(call_gpt, question, options, passage)


def get_question_number(page):
    panel = page.locator(".question_area[id^='qno_']:visible")
    if panel.count() == 1:
        panel_match = re.fullmatch(r"qno_(\d+)", panel.get_attribute("id") or "")
        if panel_match:
            return int(panel_match.group(1))
    # Question numbers restart at 1 in every section, while radio/question IDs
    # remain global (Verbal 1-17, the next section starts at 18, etc.).
    visible_radio = page.locator("input[name^='radio_']:visible").first
    name = visible_radio.get_attribute("name") if visible_radio.count() else ""
    match = re.fullmatch(r"radio_(\d+)", name or "")

    if not match:
        body_text = page.locator("body").inner_text()
        match = re.search(r"Question No:\s*(\d+)", body_text)

    if not match:

        raise RuntimeError(
            "Could not determine question number."
        )

    return int(match.group(1))

def extract_question(page, question_no):
    question_container = page.locator(f"#qno_{question_no}:visible")
    if question_container.count() != 1:
        marker = page.get_by_text(
            re.compile(r"Question No:\s*\d+"),
            exact=True
        ).filter(visible=True)
        question_container = marker.locator("xpath=../..")

    full_text = (
        question_container
        .inner_text()
        .strip()
    )

    options = {}

    for letter in ["a", "b", "c", "d"]:

        selector = (
            f"input[name='radio_{question_no}']"
            f"[value='{letter}']"
        )

        radio = page.locator(
            selector
        )

        if radio.count() == 0:

            raise RuntimeError(
                f"Radio button not found: {letter.upper()}"
            )

        row = radio.locator(
            "xpath=ancestor::tr[1]"
        )

        options[letter.upper()] = (
            row
            .inner_text()
            .strip()
        )

    option_a = options["A"]

    a_index = full_text.find(
        option_a
    )

    if a_index != -1:

        content = full_text[:a_index].strip()

    else:

        content = full_text

    marker_text = (
        f"Question No: {question_no}"
    )

    marker_index = content.find(
        marker_text
    )

    if marker_index != -1:

        content = content[
            marker_index + len(marker_text):
        ].strip()

    directions_match = re.search(
        r"DIRECTIONS\s*(?:for the question)?\s*:\s*",
        content,
        flags=re.IGNORECASE
    )

    if directions_match:

        content = content[
            directions_match.end():
        ].strip()

    blocks = re.split(
        r"\n\s*\n",
        content
    )

    blocks = [
        block.strip()
        for block in blocks
        if block.strip()
    ]

    passage = ""
    question_text = content

    if len(blocks) >= 2:

        possible_question = blocks[-1]

        looks_like_question = (
            "?" in possible_question
            or
            re.search(
                r"\b(question|objective|purpose|according|statement|"
                r"inference|conclude|imply|means|suggest|author)\b",
                possible_question,
                flags=re.IGNORECASE
            )
        )

        if looks_like_question:

            question_text = possible_question

            passage_blocks = blocks[:-1]

            passage = "\n\n".join(
                passage_blocks
            ).strip()

    if not passage:

        question_text = content.strip()

    return (
        passage,
        question_text,
        options
    )

def select_answer(
    page,
    question_no,
    answer
):

    selector = (
        f"input[name='radio_{question_no}']"
        f"[value='{answer.lower()}']"
    )

    radio = page.locator(
        selector
    )

    if radio.count() == 0:

        raise RuntimeError(
            f"Answer radio not found: {answer}"
        )

    radio.check()

    if not radio.is_checked():

        raise RuntimeError(
            "Radio selection failed."
        )

    print(
        f"[SUCCESS] Option {answer} selected."
    )

def click_save_next(page):

    save_next = page.locator(
        "a.button.savenext:visible"
    )

    if save_next.count() == 0:

        raise RuntimeError(
            "Visible Save & Next button not found."
        )

    print(
        "[Browser] Clicking Save & Next..."
    )

    save_next.click()

def wait_for_next_question(
    page,
    old_question_no
):

    for _ in range(30):

        page.wait_for_timeout(
            500
        )

        try:

            body_text = page.locator(
                "body"
            ).inner_text()

            match = re.search(
                r"Question No:\s*(\d+)",
                body_text
            )

            if match:

                new_question_no = int(
                    match.group(1)
                )

                if (
                    new_question_no
                    != old_question_no
                ):

                    return new_question_no

        except Exception:
            pass

    return None

def wait_for_question(page):
    for _ in range(60):
        try:
            body_text = page.locator("body").inner_text()
            if (
                "Question No:" in body_text
                and "Test is being downloaded" not in body_text
            ):
                return True
        except Exception:
            pass
        page.wait_for_timeout(1000)
    return False

with sync_playwright() as p:

    print("[1] Starting Playwright...")

    browser = p.chromium.launch(
        headless=False
    )

    context = browser.new_context(
        viewport=None
    )

    page = context.new_page()

    print("[2] Browser ready")

    open_login_page(page, URL)

    print("[3] Initial URL:", page.url)

    prepare_login(page)

    input(
        "\nLogin and open the test. Its sections will be detected automatically; existing answers will be kept.\n"
        "When a question and the section tabs are visible, press ENTER..."
    )

    complete = run_all_sections(
        page, get_question_number, extract_question, ask_gpt,
        select_answer, click_save_next,
    )
    status = 'All sections processed.' if complete else 'Automation stopped with questions pending.'
    input(f'\n{status} Review the browser. Press ENTER to close browser...')
    browser.close()
