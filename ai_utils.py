import re
import subprocess
import logging
import os
from typing import List
from transformers import pipeline, AutoTokenizer
from dotenv import load_dotenv

# Load environment variables from .env (make sure .env is gitignored)
load_dotenv()

# Logging to file for debugging
logging.basicConfig(filename="commit_ai_debug.log", level=logging.DEBUG, format="%(asctime)s %(message)s")

MODEL_NAME = "bigcode/santacoder"

# Load Hugging Face token securely from environment
HF_TOKEN = os.getenv("HF_TOKEN")

# Create generator and tokenizer safely (fall back to CPU if GPU not available)
try:
    generator = pipeline(
        "text-generation",
        model=MODEL_NAME,
        device=0,
        use_auth_token=HF_TOKEN
    )
except Exception:
    generator = pipeline(
        "text-generation",
        model=MODEL_NAME,
        device=-1,
        use_auth_token=HF_TOKEN
    )

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True, use_auth_token=HF_TOKEN)

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
    msg = msg.splitlines()[0].strip()
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
    prefixes = [h.split(":")[0].lower() for h in history if ":" in h]
    for p in prefixes:
        for c in candidates:
            if c.lower().startswith(p + ":"):
                return c
    files = files_text.lower()
    context = " ".join(history).lower() + " " + files
    scored = []
    for c in candidates:
        overlap = sum(1 for w in set(re.findall(r'\w+', c.lower())) if w in context)
        scored.append((overlap, c))
    scored.sort(reverse=True)
    return scored[0][1] if scored else candidates[0]

def build_prompt(history: List[str], diff_summary: str, candidates: int) -> str:
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
        l = re.sub(r'^[\d\-\)\.\s]+', '', l)
        cleaned = clean_message(l)
        if cleaned:
            lines.append(cleaned)
    return lines

def suggest_commit_message(diff_text: str = "", candidates: int = 3) -> str:
    files_summary = summarize_filenames(get_changed_files())
    if files_summary:
        diff_text = files_summary

    if not diff_text.strip():
        files = get_changed_files()
        if not files:
            return "⚠️ No staged changes to commit"
        diff_text = summarize_filenames(files)

    if len(diff_text.splitlines()) > 20:
        files = get_changed_files()
        if files:
            diff_text = summarize_filenames(files)
        else:
            diff_text = "\n".join(diff_text.splitlines()[:20])

    history_raw = run_cmd(["git", "log", "--pretty=format:%s", "-n", "5"])
    history = history_raw.splitlines() if history_raw else []

    prompt = build_prompt(history, diff_text, candidates)
    if token_count(prompt) > MAX_CONTEXT_TOKENS:
        prompt = build_prompt(history[-1:] if history else [], summarize_filenames(get_changed_files()), candidates)

    logging.debug("PROMPT:\n%s", prompt)
    logging.debug("TOKEN_COUNT: %d", token_count(prompt))

    raw_outputs = []
    for i in range(candidates):
        try:
            out = generator(
                prompt,
                max_new_tokens=MAX_CANDIDATE_TOKENS,
                truncation=True,
                do_sample=(i != 0),
                temperature=0.6,
                top_p=0.9
            )[0]["generated_text"]
        except Exception as e:
            logging.exception("Generation failed: %s", e)
            out = ""
        raw_outputs.append(out)
        logging.debug("RAW_OUTPUT_%d:\n%s", i, out)

    lines = []
    for out in raw_outputs:
        if not out:
            continue
        lines.extend(extract_candidates_from_output(out))

    seen = set()
    deduped = []
    for c in lines:
        if c.lower() not in seen:
            seen.add(c.lower())
            deduped.append(c)

    logging.debug("CLEANED_CANDIDATES: %s", deduped)

    if not deduped:
        files_text = get_changed_files().lower()
        if "readme" in files_text or "doc" in files_text:
            return "docs: update documentation"
        if "test" in files_text:
            return "test: update tests"
        if "package.json" in files_text or "requirements" in files_text:
            return "chore: update dependencies"
        names = [n.split("/")[-1] for n in files_text.splitlines() if n]
        if names:
            return f"chore: update {', '.join(names[:3])}"
        return "chore: update project files"

    best = rank_candidates(deduped, history, get_changed_files())
    logging.debug("SELECTED: %s", best)
    return best