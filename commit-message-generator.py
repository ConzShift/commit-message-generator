# commit_message_generator.py

def generate_commit_message():
    # Ask for commit type (feature, fix, docs, etc.)
    commit_type = input("Enter commit type (feat, fix, docs, chore): ").strip()

    # Ask for scope (optional, e.g. 'auth', 'UI')
    scope = input("Enter scope (optional, e.g. auth, UI): ").strip()

    # Ask for description
    description = input("Enter commit description: ").strip()

    # Build commit message
    if scope:
        commit_message = f"{commit_type}({scope}): {description}"
    else:
        commit_message = f"{commit_type}: {description}"

    print("\nGenerated commit message:")
    print(commit_message)


if __name__ == "__main__":
    generate_commit_message()