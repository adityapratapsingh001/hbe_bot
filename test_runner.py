"""Visit every question in every section and verify saved selections."""

import re
from datetime import datetime
from pathlib import Path

def section_controls(page):
    """Use the current test's visible tabs, regardless of category names."""
    tabs = page.locator("#section .section_change:visible")
    if not tabs.count():
        tabs = page.locator(".section_change:visible")
    if not tabs.count():
        tabs = page.locator("#tabs button:visible, #tabs input:visible, [role='tab']:visible")
    return tabs


def discover_sections(page):
    """Read the selected test's section tabs in their displayed order."""
    tabs = section_controls(page)
    names = tabs.evaluate_all(r"""elements => elements.map(element =>
        (element.innerText || element.value || element.textContent || '')
            .replace(/\s+/g, ' ').trim()).filter(Boolean)
    """)
    if not names or len(names) != len({name.casefold() for name in names}):
        raise RuntimeError("Could not identify a unique list of section tabs in this test.")
    return names


def wait_for_question(page, get_question_number, expected=None):
    for _ in range(60):
        try:
            number = get_question_number(page)
            if expected is None or number == expected:
                if page.locator(f"#qno_{number}:visible").count() == 1:
                    return number
                page.locator(f"input[name='radio_{number}']:visible").first.wait_for(
                    state="visible", timeout=1000
                )
                return number
        except Exception:
            pass
        page.wait_for_timeout(500)
    raise RuntimeError(f"Question did not load (expected {expected}).")


def find_test_surface(page):
    """The login site may open the actual test in another tab or an iframe."""
    owner = page if hasattr(page, "context") else page.page
    matches = []
    for candidate in reversed(owner.context.pages):
        if candidate.is_closed():
            continue
        for frame in candidate.frames:
            try:
                text = frame.locator("body").inner_text(timeout=1500)
                if (re.search(r"Question No:\s*\d+", text)
                        and (frame.locator("input[name^='radio_']:visible").count()
                             or frame.locator(".question_area[id^='qno_']:visible").count())):
                    matches.append(candidate if frame == candidate.main_frame else frame)
            except Exception:
                continue
    if len(matches) != 1:
        raise RuntimeError(
            f"Found {len(matches)} test pages/frames in {len(owner.context.pages)} browser tab(s). "
            "Open the test question in the launched browser and close any duplicate test tabs."
        )
    return matches[0]


def section_tab(page, name):
    actual_tabs = section_controls(page)
    if actual_tabs.count():
        labels = actual_tabs.evaluate_all("""elements => elements.map(element =>
            element.innerText || element.value || element.textContent || '')""")
        for index, text in enumerate(labels):
            if " ".join(text.split()).casefold() == name.casefold():
                return actual_tabs.nth(index)
    # Prefer actual controls: a heading and a clickable tab may share the same text.
    controls = page.locator(
        "a:visible, button:visible, input[type='button']:visible, "
        "input[type='submit']:visible, [role='tab']:visible, [onclick]:visible"
    )
    indices = controls.evaluate_all(r"""(elements, name) => {
        const norm = text => (text || '').replace(/\s+/g, ' ').trim().toLowerCase();
        const matches = elements.filter(el => [el.innerText, el.textContent, el.value,
            el.getAttribute('aria-label'), el.title].some(text => norm(text) === norm(name)));
        return matches.filter(el => !matches.some(other => other !== el && el.contains(other)))
            .map(el => elements.indexOf(el));
    }""", name)
    if len(indices) == 1:
        return controls.nth(indices[0])
    label = re.compile(
        r"^\s*" + r"\s+".join(re.escape(word) for word in name.split()) + r"\s*$",
        re.IGNORECASE,
    )
    text_matches = page.get_by_text(label).filter(visible=True)
    if not indices and text_matches.count() == 1:
        return text_matches
    raise RuntimeError(
        f"Section {name!r}: {len(indices)} matching controls, "
        f"{text_matches.count()} matching text elements."
    )


def save_navigation_debug(page):
    directory = Path(__file__).resolve().parent / "debug"
    directory.mkdir(exist_ok=True)
    path = directory / f"navigation_{datetime.now():%Y-%m-%d_%H-%M-%S_%f}.html"
    try:
        path.write_text(page.content(), encoding="utf-8")
        print(f"[DEBUG] Page HTML saved: {path}")
    except Exception as error:
        print(f"[DEBUG] Could not save page HTML: {error}")


def open_section(page, name, get_question_number):
    tab = section_tab(page, name)
    tab.click()
    page.wait_for_timeout(750)
    wait_for_question(page, get_question_number)


def question_numbers(page):
    text = page.locator("body").inner_text()
    match = re.search(r"Total Questions\s*:\s*(\d+)", text, re.IGNORECASE)
    if not match:
        raise RuntimeError("Could not read this section's question count.")
    total = int(match.group(1))
    # Hitbullseye repeats the current question number outside the palette.
    # Read the palette's data-qno attributes so that number is not counted twice.
    section_palettes = page.locator("#question_buttons .allsection")
    active_values = section_palettes.evaluate_all("""elements => elements
        .filter(element => getComputedStyle(element).display !== 'none')
        .flatMap(element => [...element.querySelectorAll('.buttonslist[data-qno]')]
            .map(button => button.dataset.qno))
    """) if section_palettes.count() else []
    if active_values:
        numbers = sorted({
            int(value) for value in active_values if value and value.isdigit()
        })
    else:
        # Fallback used by alternate page layouts and the offline fixture.
        palette = page.locator("#question_buttons:visible, #palette:visible").first
        numbers = sorted({
            int(value.strip()) for value in
            palette.get_by_text(re.compile(r"^\s*\d+\s*$")).filter(visible=True).all_text_contents()
        }) if palette.count() else []
    if not total or len(numbers) != total:
        raise RuntimeError(
            f"Palette has {len(numbers)} question numbers; section reports {total}. "
            "Cannot safely determine all questions."
        )
    return numbers


def open_question(page, number, get_question_number):
    target = page.locator(
        f"#question_buttons .buttonslist[data-qno='{number}']"
    )
    if target.count() == 0:
        palette = page.locator("#question_buttons:visible, #palette:visible").first
        target = palette.get_by_text(
            re.compile(rf"^\s*{number}\s*$")
        ).filter(visible=True) if palette.count() else target
    if target.count() != 1:
        raise RuntimeError(f"Could not uniquely locate palette question {number}.")
    target.click()
    wait_for_question(page, get_question_number, number)


def has_question_images(page, number):
    container = page.locator(f"#qno_{number}:visible")
    if container.count() != 1:
        marker = page.get_by_text(
            re.compile(r"Question No:\s*\d+"), exact=True
        ).filter(visible=True)
        container = marker.locator("xpath=../..")
    return container.locator("img:visible, svg:visible, canvas:visible").count() > 0


def checked_answer(page, number):
    selected = page.locator(f"input[name='radio_{number}']:visible:checked")
    if selected.count() == 1:
        value = (selected.get_attribute("value") or "").upper()
        if value in "ABCD" and len(value) == 1:
            return value
    return None


def run_all_sections(page, get_question_number, extract_question, ask_gpt,
                     select_answer, click_save_next, input_fn=input):
    verified = 0
    while True:
        try:
            page = find_test_surface(page)
            sections = discover_sections(page)
            print("[SECTIONS DETECTED] " + " -> ".join(sections))
            break
        except Exception as error:
            print(f"[PAUSED] Cannot identify the test sections: {error}")
            save_navigation_debug(page)
            if input_fn("Press ENTER to retry detection, or type stop: ").strip().lower() == "stop":
                return False
    for section in sections:
        while True:
            try:
                page = find_test_surface(page)
                open_section(page, section, get_question_number)
                numbers = question_numbers(page)
                break
            except Exception as error:
                print(f"[PAUSED] {section}: {error}. All sections are NOT complete.")
                save_navigation_debug(page)
                action = input_fn("Section navigation failed. Press ENTER to retry, or type stop: ")
                if action.strip().lower() == "stop":
                    return False
        print(f"\n[SECTION] {section}: {len(numbers)} questions")
        for number in numbers:
            while True:
                try:
                    # Return explicitly to the section; Save & Next can switch sections.
                    open_section(page, section, get_question_number)
                    open_question(page, number, get_question_number)
                    print(f"[QUESTION] {section} / {number}")
                    if page.locator(f"input[name='radio_{number}']:visible").count() == 0:
                        print(
                            f"[MANUAL REQUIRED] {section} / {number} has no A/B/C/D radio choices. "
                            "This script supports multiple-choice questions; complete this question manually."
                        )
                        print("[STOPPED] Non-MCQ question remains; test is not complete.")
                        return False
                    answer = checked_answer(page, number)
                    if answer:
                        print(f"[KEPT] Existing option {answer}")
                    else:
                        if has_question_images(page, number):
                            answer = input_fn(
                                "[IMAGE QUESTION] Text API cannot read the diagram. "
                                "Enter A/B/C/D after reviewing it, or stop: "
                            ).strip().upper()
                            if answer == "STOP":
                                print("[STOPPED] Image question pending; test is not complete.")
                                return False
                            if answer not in ("A", "B", "C", "D"):
                                raise ValueError("Enter a single option letter for this image question.")
                        else:
                            passage, question, options = extract_question(page, number)
                            print("[QUESTION TEXT]", question)
                            answer = ask_gpt(question, options, passage)
                        if get_question_number(page) != number:
                            raise RuntimeError("Question changed while waiting for the answer.")
                        select_answer(page, number, answer)
                    click_save_next(page)
                    page.wait_for_timeout(750)
                    # Revisiting catches a click that did not persist the selected radio.
                    open_section(page, section, get_question_number)
                    open_question(page, number, get_question_number)
                    if checked_answer(page, number) != answer:
                        raise RuntimeError("Answer did not remain selected after Save & Next.")
                    verified += 1
                    print(f"[VERIFIED] {section} / {number}: {answer} ({verified} total)")
                    break
                except Exception as error:
                    print(f"[PAUSED] {section} / {number}: {error}")
                    action = input_fn("Press ENTER to retry this question, or type stop: ")
                    if action.strip().lower() == "stop":
                        print("[STOPPED] Questions remain; test is not complete.")
                        return False
        print(f"[SECTION COMPLETE] {section}: {len(numbers)} answers verified")
    print(f"[COMPLETE] All {len(sections)} sections processed; {verified} answers verified.")
    print("Review the answers in the browser. The script has not clicked Submit test.")
    return True
