import subprocess
from tkinter import messagebox, END

def generate_commit(type_var, scope_entry, desc_entry, breaking_var, preview_text):
    ctype = type_var.get()
    scope = scope_entry.get().strip()
    desc = desc_entry.get().strip()
    breaking = breaking_var.get()

    if not desc:
        messagebox.showerror("Error", "Description cannot be empty")
        return

    commit_msg = f"{ctype}({scope}): {desc}" if scope else f"{ctype}: {desc}"
    if breaking:
        commit_msg += f"\n\nBREAKING CHANGE: {desc}"

    preview_text.config(state="normal")
    preview_text.delete("1.0", END)
    preview_text.insert(END, commit_msg)
    preview_text.config(state="disabled")

def commit_now(repo_path, preview_text, file_vars, check_changes, load_files, load_history, preview_status=None):
    commit_msg = preview_text.get("1.0", "end").strip()
    if not commit_msg:
        if preview_status:
            preview_status.config(text="⚠️ No commit message generated")
        messagebox.showerror("Error", "No commit message generated")
        return
    if not repo_path:
        if preview_status:
            preview_status.config(text="⚠️ No repository selected")
        messagebox.showerror("Error", "No repository selected")
        return

    try:
        selected_files = [f for f, var in file_vars.items() if var.get()]
        if not selected_files:
            subprocess.run(["git", "-C", repo_path, "add", "."], check=True)
        else:
            for f in selected_files:
                subprocess.run(["git", "-C", repo_path, "add", f], check=True)

        subprocess.run(["git", "-C", repo_path, "commit", "-m", commit_msg], check=True)
        messagebox.showinfo("Success", f"Commit created successfully in {repo_path}!")
        check_changes()
        load_files()
        load_history()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Git Error", f"Failed to commit: {e}")