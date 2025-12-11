# Commit Message Generator 📝

A simple Python tool that helps developers generate **Conventional Commit** messages consistently.  
This project is meta — it can even commit itself using the messages it generates!

---

## 🚀 Features
- Prompt‑based commit message generator (type, scope, description).
- Supports **Conventional Commits** format.
- Handles **breaking changes** with proper annotation.
- Optionally auto‑stages changes and runs `git commit`.
- Multiline commit message support (via temp file).
- Clear feedback with ✅ / ❌ indicators.

---

## 📦 Installation
Clone the repo:
  ```bash
    git clone https://github.com/ConzShift/commit-message-generator.git
    cd commit-message-generator
```
## ▶️ Usage 🖥️
Run the script:
```bash
python commit_message_generator.py
```
Follow the prompts:
- Enter commit type (feat, fix, docs, chore, refactor, test, style, perf).
- Enter scope (optional, e.g. auth, UI).
- Enter description.
- Mark if it’s a breaking change.
- Choose whether to commit directly.

## 💡 Example
- Enter commit type ['feat', 'fix', 'docs', 'chore', 'refactor', 'test', 'style']
- Enter scope (optional, e.g. auth, UI): commit-generator
- Enter commit description: add working commit message generator script
- Is this a breaking change? (y/n): n
- Do you want to commit with this message? (y/n): y

## 📦 Result

[main cf7ce92] feat(commit-generator): add working commit message generator script
 1 file changed, 44 insertions(+), 4 deletions(-)
🎉 Commit created successfully!

## 🎯 Why This Project
- Enforces commit consistency across projects.
- Saves time writing commit messages.
- Demonstrates orchestration skills and AI‑assisted tooling.
- Meta milestone: the app can commit itself!
