"""Build complete question prompts and handle non-answer responses."""

import re


def parse_answer(response):
    text = response.strip()
    match = re.fullmatch(r"\s*\**([ABCD])\**[.)]?\s*", text, re.IGNORECASE)
    if not match:
        match = re.fullmatch(
            r"\s*\**(?:final\s+answer|answer)\s*:\s*\**([ABCD])\**[.]?\s*",
            text,
            re.IGNORECASE,
        )
    return match.group(1).upper() if match else None


def solve_question(call_gpt, question, options, passage=""):
    if not question.strip() or any(not options.get(key, "").strip() for key in "ABCD"):
        raise ValueError("Question or answer choices are missing; no request sent.")

    # Send the full passage first, followed by the question and all choices.
    content = f"FULL PASSAGE:\n{passage}\n\n" if passage.strip() else ""
    content += f"QUESTION:\n{question}\n\nANSWER CHOICES:\n" + "\n".join(
        f"{key}) {options[key]}" for key in "ABCD"
    )

    for attempt in range(2):
        instruction = (
            "Return only the correct answer letter: A, B, C, or D. "
            "Do not include an explanation or the option text. "
            "Read the full passage, question, and answer choices below, then choose the correct answer."
        )
        if attempt:
            instruction += (
                " The previous request received no usable answer. "
                "The complete question, all choices, and any passage are included below. "
                "Solve this question now."
            )
        prompt = f"{instruction}\n\n{content}"
        raw_answer = call_gpt(prompt)
        print("[GPT] Raw response:", raw_answer)
        answer = parse_answer(raw_answer)
        if answer:
            print("[GPT] Selected:", answer)
            return answer
        if attempt == 0:
            print("[GPT] No valid option returned. Retrying once with the full question...")

    raise RuntimeError(
        "GPT returned no valid option after two complete requests. "
        "No answer was selected. Inspect the prompt and response files in prompts/. "
        "The API may not be passing the complete prompt to its model. "
        f"Last response: {raw_answer}"
    )
