"""Save the exact prompt for each outgoing GPT request."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4


def prepare_prompt(prompt):
    # This endpoint mishandles multiline input; retain every line's text in order.
    return prompt.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def save_prompt(prompt):
    directory = Path(__file__).resolve().parent / "prompts"
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    path = directory / f"prompt_{timestamp}_{uuid4().hex}.txt"
    with path.open("x", encoding="utf-8", newline="") as output:
        output.write(prompt)
    print("[GPT] Prompt saved:", path)
    return path
