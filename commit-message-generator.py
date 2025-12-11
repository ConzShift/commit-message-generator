# commit_message_generator.py

import subprocess
import tempfile
import os

def generate_commit_message():
    # Valid commit types (Conventional Commits)
    valid_types = ["feat", "fix", "docs", "chore", "refactor", "test", "style", "perf"]

    # Ask for commit type
    commit_type = input(f"Enter commit type {valid_types}: ").strip()
    if commit_type not in valid_types:
        print("❌ Invalid type! Please choose from:", ", ".join(valid_types))
        return

    # Ask for scope (optional)
    scope = input("Enter scope (optional, e.g. auth, UI): ").strip()

    # Ask for description
    description = input("Enter commit description: ").strip()
    if not description:
        print("❌ Description cannot be empty.")
        return

    # Build commit message
    if scope:
        commit_message = f"{commit_type}({scope}): {description}"
    else:
        commit_message = f"{commit_type}: {description}"

    # Ask if breaking change
    breaking = input("Is this a breaking change? (y/n): ").strip().lower()
    if breaking == "y":
        commit_message += "\n\nBREAKING CHANGE: " + description

    print("\n✅ Generated commit message:")
    print(commit_message)

    # Ask if user wants to commit directly
    auto_commit = input("\nDo you want to commit with this message? (y/n): ").strip().lower()
    if auto_commit == "y":
        try:
            # Stage all changes automatically
            subprocess.run(["git", "add", "."], check=True)

            if "\n" in commit_message:
                # Handle multiline commit message using a temp file
                with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmpfile:
                    tmpfile.write(commit_message)
                    tmpfile.flush()
                    subprocess.run(["git", "commit", "-F", tmpfile.name], check=True)
                os.unlink(tmpfile.name)  # cleanup temp file
            else:
                subprocess.run(["git", "commit", "-m", commit_message], check=True)

            print("🎉 Commit created successfully!")
        except subprocess.CalledProcessError:
            print("❌ Error: Could not run git commit. Make sure you have a valid Git repo.")
        except FileNotFoundError:
            print("❌ Error: Git is not installed or not found in PATH.")

if __name__ == "__main__":
    generate_commit_message()