import torch
import re
from transformers import pipeline

# Global generator placeholder
_generator = None

def get_generator():
    """
    Lazily initialize the Hugging Face pipeline.
    Loads StarCoderBase only once, on first use.
    Falls back to a smaller model if GPU memory is insufficient.
    """
    global _generator
    if _generator is None:
        print("Loading model... this may take a while")

        # Detect GPU availability
        device = 0 if torch.cuda.is_available() else -1

        try:
            _generator = pipeline(
                "text-generation",
                model="bigcode/starcoderbase",   # gated model
                token="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",
                device=device,
                torch_dtype="auto",
                device_map="auto",
                offload_folder="offload"  # ensure disk offload works
            )
            print("✅ StarCoderBase finished loading")
        except Exception as e:
            print(f"⚠️ Could not load StarCoderBase: {e}")
            print("Falling back to smaller model (SantaCoder)")
            _generator = pipeline(
                "text-generation",
                model="bigcode/santacoder",
                token="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",
                device=device
            )
            print("✅ SantaCoder finished loading")

    return _generator


def clean_diff(diff_text: str) -> str:
    """
    Simplify the diff by keeping only added/removed code lines.
    Skip metadata like file paths, index lines, and headers.
    """
    lines = []
    current_file = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 3:
                current_file = parts[2].replace("b/", "")
        elif line.startswith("index") or line.startswith("---") or line.startswith("+++"):
            continue
        elif line.startswith("+") and not line.startswith("+++"):
            lines.append(f"{current_file or 'file'}: added {line[1:60].strip()}")
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(f"{current_file or 'file'}: removed {line[1:60].strip()}")
    return "\n".join(lines[:20])  # cap at 20 summaries


def suggest_commit_message(diff_text: str) -> str:
    """
    Generate a concise commit message using StarCoderBase (or fallback).
    Falls back to a safe default if the AI output is empty or junk.
    """
    short_diff = clean_diff(diff_text)[:500]
    prompt = (
        "Write a one-line git commit message in plain English. "
        "Follow Conventional Commit style (feat:, fix:, chore:, etc.). "
        "Do not output code, numbers, symbols, variable names, or unusual characters. "
        "Keep it concise and professional.\n"
        f"{short_diff}\nCommit message:"
    )

    generator = get_generator()
    result = generator(
        prompt,
        max_new_tokens=50,
        truncation=True,
        do_sample=False,   # deterministic output
        temperature=0.3    # lower randomness
    )
    suggestion = result[0]["generated_text"].split("Commit message:")[-1].strip()
    suggestion = suggestion.split("\n")[0]

    # Cleanup: remove junk characters
    suggestion = re.sub(r'[^a-zA-Z\s:]', '', suggestion)

    # Fallback if model outputs junk
    if not suggestion or len(suggestion.split()) < 2 or suggestion.lower() in ("change", "update", "fix"):
        suggestion = "chore: update project files"

    return suggestion