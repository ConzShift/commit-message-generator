# debug_commit_ai.py
import logging
import os
import subprocess
import re
from logging.handlers import RotatingFileHandler

LOG_PATH = os.path.expanduser(r"~\\commit_ai_debug.log")

logger = logging.getLogger("commit_ai_debug")
logger.setLevel(logging.DEBUG)
file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(file_formatter)
logger.addHandler(console_handler)

logger.debug("Logging initialized to %s", LOG_PATH)

MODEL_NAME = "gpt2-large"

def run(cmd):
    try:
        return subprocess.check_output(cmd, text=True, encoding="utf-8", errors="ignore").strip()
    except Exception as e:
        logger.exception("Command failed: %s", cmd)
        return ""

def get_changed_files():
    return run(["git", "diff", "--staged", "--name-only"])

def get_staged_diff(max_chars=1500):
    diff = run(["git", "diff", "--staged", "--unified=1", "--no-color"])
    if not diff:
        return ""
    diff = re.sub(r'^\+\+\+.*|^---.*', '', diff, flags=re.MULTILINE)
    return diff[:max_chars]

def summarize_filenames(files_text: str) -> str:
    files = [f.strip() for f in files_text.splitlines() if f.strip()]
    if not files:
        return ""
    return "Changed files: " + ", ".join(files[:10]) + (", ..." if len(files) > 10 else "")

def load_seed_examples():
    path = "commit_examples.txt"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
                if lines:
                    logger.info("Loaded %d seed examples from %s", len(lines), path)
                    print("\nUSING SEED EXAMPLES FROM FILE:\n", "\n".join(lines[:10]))
                    return lines[:10]
        except Exception as e:
            logger.warning("Failed to read %s: %s", path, e)

    history_raw = run(["git", "log", "--pretty=format:%s", "-n", "8"])
    lines = history_raw.splitlines() if history_raw else []
    examples = [l for l in lines if ":" in l][:5]
    if examples:
        logger.info("Using %d seed examples from git history", len(examples))
        print("\nUSING SEED EXAMPLES FROM GIT HISTORY:\n", "\n".join(examples))
        return examples
    return ["chore: update project files"]

def build_prompt(seed_examples, diff_summary, diff_text, candidates=3, tok=None, max_tokens=800):
    examples_block = "\n".join(seed_examples)
    prompt = (
        "Example commits:\n"
        f"{examples_block}\n\n"
        "Rules:\n"
        "- Write Conventional Commit messages.\n"
        "- Format: type: description\n"
        "- Imperative mood, under 12 words.\n"
        "- Summarize actual changes from DIFF.\n"
        "- Do not copy code. Write only commit messages.\n"
        "- Only output commit messages. Do not include code, comments, or stack traces.\n\n"
        f"{diff_summary}\n\n"
        "DIFF:\n"
        f"{diff_text}\n\n"
        f"Write {candidates} messages:\n"
        "1. "
    )
    if tok is not None:
        ids = tok.encode(prompt)
        print(f"\nPROMPT TOKEN LENGTH: {len(ids)}")
        if len(ids) > max_tokens:
            ids = ids[:max_tokens]
            prompt = tok.decode(ids)
            print(f"Truncated prompt to {max_tokens} tokens.")
    return prompt

def safe_init_model(model_name=MODEL_NAME):
    try:
        from transformers import pipeline, AutoTokenizer
    except Exception as e:
        logger.exception("transformers import failed: %s", e)
        return None, None
    try:
        gen = pipeline("text-generation", model=model_name, device=-1)
        tok = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        try:
            gen.model.config.pad_token_id = gen.model.config.eos_token_id
        except Exception:
            pass
        logger.debug("Initialized model pipeline for %s", model_name)
        return gen, tok
    except Exception as e:
        logger.exception("Model init failed: %s", e)
        return None, None

def post_process_continuation(out: str) -> str:
    if not out:
        return ""
    out = re.sub(r'[_\-,\s]{3,}$', "", out).strip()
    out = re.sub(r'[^\x09\x0A\x0D\x20-\x7E]', "", out)
    return out.strip()

def clean_candidate_line(line: str) -> str:
    if not line:
        return ""
    s = line.strip()
    # Drop junk echoes
    if s.lower().startswith("exception") or "return None" in s or "print(" in s or "traceback" in s.lower() or s.startswith("#"):
        return ""
    s = re.sub(r'^[\s\-\)\(\[\]]*\d+[\.\)]\s*', '', s)
    s = re.sub(r'^[\s\-\*]+', '', s)
    s = re.split(r'(?<=\w)\.\s', s)[0].strip()
    s = re.sub(r'^(feat|FEAT)\s*:', 'feat:', s)
    s = re.sub(r'^(fix|FIX)\s*:', 'fix:', s)
    s = re.sub(r'^(chore|CHORE)\s*:', 'chore:', s)
    s = re.sub(r'^(docs|DOCS)\s*:', 'docs:', s)
    s = re.sub(r'^(refactor|REFACTOR)\s*:', 'refactor:', s)
    if s.lower().startswith("changed files"):
        return ""
    if ":" not in s:
        if re.search(r'\bfix|bug|error|typo\b', s, flags=re.I):
            s = "fix: " + s
        else:
            s = "feat: " + s
    s_words = s.split()
    if len(s_words) > 12:
        s = " ".join(s_words[:12])
    return s.strip()

def main():
    files = get_changed_files()
    diff_summary = summarize_filenames(files) if files else ""
    if not diff_summary:
        print("No staged files. Stage one small change and re-run.")
        return

    diff_text = get_staged_diff(max_chars=1500)
    seed_examples = load_seed_examples()

    gen, tok = safe_init_model()
    if gen is None:
        print("Model init failed; check commit_ai_debug.log for details.")
        return

    prompt = build_prompt(seed_examples, diff_summary, diff_text, candidates=3, tok=tok)
    logger.debug("PROMPT:\n%s", prompt)
    print("\nPROMPT FED TO MODEL:\n", prompt[:500], "...")

    raw_outputs = []
    for i in range(3):
        try:
            gen_kwargs = {
                "max_new_tokens": 60,
                "do_sample": True,
                "top_p": 0.92,
                "return_full_text": False,
            }
            out = gen(prompt, **gen_kwargs)[0].get("generated_text", "")
        except Exception as e:
            logger.exception("Generation failed: %s", e)
            out = ""
        out_clean = post_process_continuation(out)
        raw_outputs.append(out_clean)
        print(f"\nRAW_OUTPUT_{i} (first 400 chars):\n", out_clean[:400])

    candidates = []
    for out in raw_outputs:
        if not out:
            continue
        for l in out.splitlines():
            cleaned = clean_candidate_line(l)
            if cleaned:
                candidates.append(cleaned)

    seen = set()
    deduped = []
    for c in candidates:
        key = c.lower()
        if key and key not in seen and ":" in c and len(c.split()) <= 12:
            seen.add(key)
            deduped.append(c)

    print("\nCLEANED_CANDIDATES:", deduped)

    if not deduped:
        names = [n.split("/")[-1] for n in files.splitlines() if n]
        fallback = f"chore: update {', '.join(names[:3])}" if names else "chore: update project files"
        print("\nFALLBACK:", fallback)
        return

    selected = deduped[0]
    print("\nSELECTED:", selected)
    print("\nWrote logs to:", LOG_PATH)

if __name__ == "__main__":
    main()