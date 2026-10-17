from prompt_logging import prepare_prompt, save_prompt


def ask_gpt(question, options):

    prompt = f"""
You are solving a multiple-choice practice test.

QUESTION:
{question}

OPTIONS:

A. {options["A"]}
B. {options["B"]}
C. {options["C"]}
D. {options["D"]}

IMPORTANT:
Return ONLY the single correct option letter.

Valid responses:
A
B
C
D

Do NOT provide explanation.
Do NOT return the option text.
"""

    prompt = prepare_prompt(prompt)
    print("\n[GPT] Sending request...")
    print("[GPT] Prompt length:", len(prompt))

    try:
        save_prompt(prompt)
        response = requests.post(
            GPT_URL,
            json={
                "prompt": prompt
            },
            timeout=120
        )

        print("[GPT] HTTP status:", response.status_code)
        print("[GPT] Server response:")
        print(response.text)

        response.raise_for_status()

    except requests.exceptions.RequestException as e:

        print("\n========== GPT API ERROR ==========")
        print(e)

        if e.response is not None:
            print(
                "Status:",
                e.response.status_code
            )
            print(
                "Response:",
                e.response.text
            )

        raise

    data = response.json()

    raw_answer = str(
        data.get("response", "")
    ).strip()

    print(
        "[GPT] Raw answer:",
        raw_answer
    )

    match = re.search(
        r"(?<![A-Za-z])([ABCD])(?![A-Za-z])",
        raw_answer.upper()
    )

    if not match:

        raise RuntimeError(
            "Could not extract A/B/C/D "
            f"from GPT response:\n{raw_answer}"
        )

    answer = match.group(1)

    print(
        f"[GPT] Selected: {answer}"
    )

    return answer
