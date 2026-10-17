# HYE Bot

A Python script for working through Hitbullseye multiple-choice mock tests. It opens Chromium, fills the login credentials, detects the test's sections, sends questions to a configured answer API, selects answers, and checks that they remain selected after Save & Next.

**Main script:** `open_test_fixed.py`.

## Quick start — existing setup

Open PowerShell in the project folder:

```powershell
cd D:\hye-bot
.\venv\Scripts\Activate.ps1
python -u open_test_fixed.py
```

Before starting, run your answer API service. The main script currently expects it at:

```text
http://localhost:3102/v1/generate
```

The API server is a separate service; this project does not contain its startup code.

If activating the environment is blocked, run Python directly:

```powershell
cd D:\hye-bot
.\venv\Scripts\python.exe -u open_test_fixed.py
```

## First-time setup

You need Windows, PowerShell, Python, an internet connection for Hitbullseye, and access to a compatible answer API. The existing environment was created with Python 3.13.

For a fresh checkout without a working virtual environment:

```powershell
cd D:\hye-bot
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m playwright install chromium
```

Use your actual project path if it is not `D:\hye-bot`.

## Configure login

The script reads `login_credentials.json` beside the Python files:

After cloning the repository, create that local file from the included template:

```powershell
Copy-Item login_credentials.example.json login_credentials.json
```

```json
{
  "username": "YOUR_STUDENT_ID",
  "password": "YOUR_PASSWORD"
}
```

Replace the example values with your account details. Keep both values as strings and use valid JSON with double quotes. The existing file may already contain your credentials; the example above is only a template.

This file stores credentials in plain text. Keep it private. The project's `.gitignore` excludes it, the virtual environment, prompts, and debug captures from Git. Debug HTML may also contain account or test information.

Autofill runs only on `hitbullseye.com` and its subdomains. It fills the fields; you click Login yourself.

## Run the mock test

1. Start the answer API service, then run `python -u open_test_fixed.py`.
2. Wait for the script's Chromium browser to open. The initial URL may redirect to the Hitbullseye homepage.
3. Open the login form if necessary. The script looks for the form for about 30 seconds and fills your credentials when it finds one.
4. Click Login, select your mock test, and open it in that same browser. A new test tab or iframe within that browser is supported.
5. Once a question and the section tabs are visible, return to PowerShell and press **ENTER**.
6. Let the script process the questions. Watch the terminal for progress or requests for manual input.
7. When processing stops, review the browser before pressing the final ENTER, which closes it.

If prompted to open the login form, open it and press ENTER to retry autofill. If you are already logged in, type `skip` at that prompt.

The script does not attach to an unrelated browser window that you opened separately. Keep only one test open in the browser launched by the script so page detection is unambiguous.

## Sections and answers

Section names and their order are read from the selected test; they are not fixed to one company's mock test. For example:

```text
Technical -> Aptitude -> English Language -> Coding
```

The script reads each section's question count from the page. There is no fixed 10-question limit. It uses internal question IDs because visible question numbering can restart at 1 when the section changes.

For each question, it:

- Keeps an existing selected A/B/C/D answer instead of requesting a new one.
- Otherwise extracts the text and choices, requests an answer, and selects that option.
- Clicks Save & Next, revisits the question, and checks that the option remains selected.

Existing answers are preserved, not checked for correctness. A verified selection means it remained selected after navigation; it does not guarantee that the answer is correct.

The script does **not** click Submit test. Review the answers and submit manually when ready. Browser sessions are not saved between script launches; resuming depends on the answers retained by the website after you log in again.

## Questions requiring manual work

The automatic solver supports text questions with four A/B/C/D radio choices.

- **Images, diagrams, SVGs, or canvas content:** the script asks you to review the question in the browser and enter `A`, `B`, `C`, or `D` in the terminal. Type `stop` to end processing instead.
- **Coding or other questions without A/B/C/D radio choices:** the script stops with `MANUAL REQUIRED`. Complete those questions manually. A section named Coding is processed automatically only when its questions have supported multiple-choice inputs.
- **Missing or ambiguous page elements:** processing pauses instead of reporting completion.

## Answer API configuration

Edit `GPT_URL` near the top of `open_test_fixed.py` to change the API endpoint. `open_test.py` is an alternate entry script with its own endpoint setting; it is not synchronized automatically with the main script.

The main script sends a POST request with JSON:

```json
{
  "prompt": "The complete instructions, passage, question, and choices"
}
```

The expected response is a JSON object such as:

```json
{
  "success": true,
  "response": "C"
}
```

The request timeout is 120 seconds. Authentication headers are not currently configured.

Prompt order is:

1. Instructions to return only A/B/C/D.
2. The full passage, when present.
3. The question.
4. All four answer choices.

The passage is sent in full, without chunking or summarization. Line breaks are converted to spaces before sending because the previously used endpoint mishandled multiline prompts. The saved prompt contains the exact resulting text sent to the API.

A non-answer response triggers one automatic retry with the complete question. If both replies are unusable, the script pauses. Network errors also reach the pause flow. Press ENTER to retry the question, or type `stop` to stop processing.

## Prompt, response, and debug files

Files are stored relative to the script folder, regardless of the terminal's current directory.

| Location | Contents |
| --- | --- |
| `prompts/prompt_<timestamp>_<unique-id>.txt` | Exact outgoing prompt, saved before the request |
| `prompts/prompt_<timestamp>_<unique-id>.response.txt` | Raw HTTP response body for the matching request |
| `debug/navigation_<timestamp>.html` | Page HTML captured when section detection or initial section navigation fails |

Each retry creates a separate prompt file. If the request fails before an HTTP response arrives, its prompt file can exist without a response file. The terminal prints the saved paths. Files accumulate until you remove them yourself.

## Terminal messages and controls

| Message or input | Meaning |
| --- | --- |
| `[SECTIONS DETECTED]` | Names and order read from the current mock test |
| `[KEPT]` | An existing selection was preserved |
| `[VERIFIED]` | Selection remained checked after Save & Next and revisiting |
| `[PAUSED]` | A problem needs attention; processing has not completed |
| `[MANUAL REQUIRED]` | The question lacks supported multiple-choice inputs |
| `[COMPLETE]` | All detected sections were processed and selections verified |
| ENTER at a retry prompt | Retry detection, navigation, or the current question |
| `stop` at a retry prompt | Stop automation with questions pending |
| `Ctrl+C` | Interrupt the Python process; the launched browser may close |
| ENTER at the final prompt | Close the browser |

## Troubleshooting

| Problem | What to do |
| --- | --- |
| Initial page navigation times out | The browser remains open. Refresh or open the test URL manually, log in, then continue at the terminal prompt. |
| No login form found | Open the login form in the launched browser and retry. Use `skip` if already logged in. |
| Connection refused on port 3102 | Start your local answer API service, or set `GPT_URL` to the correct endpoint. |
| API asks you to send the question again | Inspect the matching prompt and response files. The full question should be in the prompt; confirm the API accepts the documented JSON format. |
| Section or palette count error | Wait for the page to load, then retry. Inspect the printed debug HTML path if it repeats; the website markup may have changed. |
| Multiple test pages detected | Close duplicate test tabs in the launched browser, leaving the intended test open. |
| Answer did not remain selected | Check the browser and connection, then retry the paused question. |
| Chromium executable missing | Run `.\venv\Scripts\python.exe -m playwright install chromium`. |
| Python dependencies missing | Run `.\venv\Scripts\python.exe -m pip install requests playwright`. |
| Changes seem ignored | Stop the running process and restart it. A running Python process does not reload edited files automatically. |

## Project files

| File | Purpose |
| --- | --- |
| `open_test_fixed.py` | Main entry point, question extraction, answer selection, and API calls |
| `open_test.py` | Alternate entry point; use the main script unless you need this version |
| `browser_startup.py` | Initial navigation, credential loading, and login autofill |
| `test_runner.py` | Test-page detection, section discovery, navigation, retries, and selection verification |
| `gpt_question.py` | Prompt construction, answer parsing, and one retry for non-answers |
| `prompt_logging.py` | Single-line prompt conversion and prompt file creation |
| `login_credentials.json` | Local login credentials |
| `ask_gpt.py` | Older helper fragment; not a standalone runner |

## Offline checks

These checks use local browser fixtures or saved HTML rather than the live test or answer API:

```powershell
.\venv\Scripts\python.exe check_login.py
.\venv\Scripts\python.exe check_section_names.py
.\venv\Scripts\python.exe check_all_sections.py
```

`check_login.py` uses dummy credentials. `check_all_sections.py` covers multiple sections, global question IDs, existing answers, and saved selections.

An additional captured-page check is available:

```powershell
.\venv\Scripts\python.exe check_saved_mock.py
```

It requires the specific saved HTML file referenced in that script. It will not run if that debug capture has been removed. Offline checks validate the supported layouts; they do not guarantee that a future website layout will work unchanged.
