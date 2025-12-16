import re
import subprocess
import logging
from typing import List
from transformers import pipeline, AutoTokenizer

# Logging to file for debugging
logging.basicConfig(filename="commit_ai_debug.log", level=logging.DEBUG, format="%(asctime)s %(message)s")

MODEL_NAME = "bigcode/santacoder"
# Create generator and tokenizer safely (fall back to CPU if GPU not available)
try:
    generator = pipeline("text-generation", model=MODEL_NAME, device=0)
except Exception:
    generator = pipeline("text-generation", model=MODEL_NAME, device=-1)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

VALID_TYPES = ("feat", "fix", "docs", "style", "refactor", "test", "chore", "perf")
MAX_CONTEXT_TOKENS = 2000  # keep a safety margin under model window
MAX_CANDIDATE_TOKENS = 120  # increased budget so model has room to produce a full message
MAX_COMMIT_LENGTH = 80

def run_cmd(cmd: List[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""

def get_changed_files() -> str:
    return run_cmd(["git", "diff", "--staged", "--name-only"])

def summarize_filenames(files_text: str) -> str:
    files = [f.strip() for f in files_text.splitlines() if f.strip()]
    if not files:
        return ""
    return "Changed files: " + ", ".join(files[:10]) + (", ..." if len(files) > 10 else "")

def clean_message(msg: str) -> str:
    # Keep punctuation useful for Conventional Commits; remove only control characters
    msg = msg.splitlines()[0].strip()
    # remove control chars (keep punctuation like : . _ - /)
    msg = re.sub(r'[\x00-\x1f\x7f]', '', msg).strip()
    if not msg:
        return ""
    if not re.match(r'^(?:' + "|".join(VALID_TYPES) + r')\s*:', msg, flags=re.IGNORECASE):
        msg = f"feat: {msg}"
    return msg[:MAX_COMMIT_LENGTH]

def token_count(text: str) -> int:
    try:
        return len(tokenizer(text)["input_ids"])
    except Exception:
        return 0

def rank_candidates(candidates: List[str], history: List[str], files_text: str) -> str:
    # 1) prefer exact prefix match to recent history
    prefixes = [h.split(":")[0].lower() for h in history if ":" in h]
    for p in prefixes:
        for c in candidates:
            if c.lower().startswith(p + ":"):
                return c
    # 2) prefer candidate that mentions filenames or keywords
    files = files_text.lower()
    context = " ".join(history).lower() + " " + files
    scored = []
    for c in candidates:
        overlap = sum(1 for w in set(re.findall(r'\w+', c.lower())) if w in context)
        scored.append((overlap, c))
    scored.sort(reverse=True)
    return scored[0][1] if scored else candidates[0]

def build_prompt(history: List[str], diff_summary: str, candidates: int) -> str:
    # Provide 2-3 curated examples if available, otherwise a short default
    examples = "\n".join(history[-3:]) if history else "chore: update project files"
    prompt = (
        "Example commits:\n"
        f"{examples}\n\n"
        "Follow the format type: description. Keep under 12 words, imperative mood.\n"
        f"Write {candidates} different Conventional Commit messages summarizing these changes:\n"
        f"{diff_summary}\nMessages:"
    )
    return prompt

def extract_candidates_from_output(raw_text: str) -> List[str]:
    # Try to extract the portion after "Messages:" or "Message:" if present
    tail = raw_text
    if "Messages:" in raw_text:
        tail = raw_text.split("Messages:")[-1]
    elif "Message:" in raw_text:
        tail = raw_text.split("Message:")[-1]
    lines = []
    for l in tail.splitlines():
        l = l.strip()
        if not l:
            continue
        # Remove leading numbering or bullets like "1. " or "- "
        l = re.sub(r'^[\d\-\)\.\s]+', '', l)
        cleaned = clean_message(l)
        if cleaned:
            lines.append(cleaned)
    return lines

def suggest_commit_message(diff_text: str = "", candidates: int = 3) -> str:
    # 0. Prefer filenames-only input when available (force compact, clear signal)
    files_summary = summarize_filenames(get_changed_files())
    if files_summary:
        diff_text = files_summary

    # 1. Early exit: nothing staged and no diff
    if not diff_text.strip():
        files = get_changed_files()
        if not files:
            return "⚠️ No staged changes to commit"
        diff_text = summarize_filenames(files)

    # 2. Prefer filenames summary if diff is long (defensive)
    if len(diff_text.splitlines()) > 20:
        files = get_changed_files()
        if files:
            diff_text = summarize_filenames(files)
        else:
            diff_text = "\n".join(diff_text.splitlines()[:20])

    # 3. Short history examples
    history_raw = run_cmd(["git", "log", "--pretty=format:%s", "-n", "5"])
    history = history_raw.splitlines() if history_raw else []

    # 4. Build prompt and ensure it fits token budget
    prompt = build_prompt(history, diff_text, candidates)
    if token_count(prompt) > MAX_CONTEXT_TOKENS:
        # aggressively shorten: keep 1 example and filenames summary
        prompt = build_prompt(history[-1:] if history else [], summarize_filenames(get_changed_files()), candidates)

    logging.debug("PROMPT:\n%s", prompt)
    logging.debug("TOKEN_COUNT: %d", token_count(prompt))

    # 5. Generate candidates: deterministic baseline + sampled variants (use global generator)
    raw_outputs = []
    for i in range(candidates):
        try:
            out = generator(
                prompt,
                max_new_tokens=MAX_CANDIDATE_TOKENS,
                truncation=True,
                do_sample=(i != 0),  # first run deterministic
                temperature=0.6,
                top_p=0.9
            )[0]["generated_text"]
        except Exception as e:
            logging.exception("Generation failed: %s", e)
            out = ""
        raw_outputs.append(out)
        logging.debug("RAW_OUTPUT_%d:\n%s", i, out)

    # 6. Extract and dedupe candidates
    lines = []
    for out in raw_outputs:
        if not out:
            continue
        lines.extend(extract_candidates_from_output(out))
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for c in lines:
        if c.lower() not in seen:
            seen.add(c.lower())
            deduped.append(c)

    logging.debug("CLEANED_CANDIDATES: %s", deduped)

    # 7. Rule-based fallback if no candidates
    if not deduped:
        files_text = get_changed_files().lower()
        if "readme" in files_text or "doc" in files_text:
            return "docs: update documentation"
        if "test" in files_text:
            return "test: update tests"
        if "package.json" in files_text or "requirements" in files_text:
            return "chore: update dependencies"
        # last resort: create a short filename-based message
        names = [n.split("/")[-1] for n in files_text.splitlines() if n]
        if names:
            return f"chore: update {', '.join(names[:3])}"
        return "chore: update project files"

    # 8. Rank and return best
    best = rank_candidates(deduped, history, get_changed_files())
    logging.debug("SELECTED: %s", best)
    return best