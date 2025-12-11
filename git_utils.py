import subprocess, os
from tkinter import messagebox, filedialog, ttk, BooleanVar

repo_path = None
file_vars = {}

def choose_repo(repo_label, check_changes, load_files, load_history):
    global repo_path
    folder = filedialog.askdirectory(title="Select Git Repository")
    if not folder:
        return
    if os.path.isdir(os.path.join(folder, ".git")):
        repo_path = folder
        repo_label.config(text=f"Repo: {repo_path}")
        messagebox.showinfo("Repo Selected", f"Using repo: {repo_path}")
        check_changes()
        load_files()
        load_history()
    else:
        messagebox.showerror("Error", "Selected folder is not a Git repository")

def check_changes(status_label, canvas, light):
    global repo_path
    if not repo_path:
        status_label.config(text="Repo status: No repository selected")
        canvas.itemconfig(light, fill="grey")
        return
    try:
        branch = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        summary = subprocess.run(
            ["git", "-C", repo_path, "status", "-sb"],
            capture_output=True, text=True, check=True
        ).stdout.strip().splitlines()[0]

        status_label.config(text=f"Branch: {branch} | {summary}")

        result = subprocess.run(
            ["git", "-C", repo_path, "status", "--short"],
            capture_output=True, text=True, check=True
        )
        changes = result.stdout.strip()
        if not changes:
            canvas.itemconfig(light, fill="green")
        else:
            staged = subprocess.run(
                ["git", "-C", repo_path, "diff", "--cached", "--name-only"],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            if staged:
                canvas.itemconfig(light, fill="red")
            else:
                canvas.itemconfig(light, fill="orange")
    except subprocess.CalledProcessError as e:
        status_label.config(text=f"Git Error: {e}")
        canvas.itemconfig(light, fill="grey")

def load_files(files_frame):
    global repo_path, file_vars
    for widget in files_frame.winfo_children():
        widget.destroy()
    file_vars.clear()

    if not repo_path:
        ttk.Label(files_frame, text="Select a repository to view changes").pack(anchor="w")
        return

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "status", "--short"],
            capture_output=True, text=True, check=True
        )
        changes = result.stdout.strip().splitlines()
        if not changes:
            ttk.Label(files_frame, text="No changes detected").pack(anchor="w")
        else:
            ttk.Label(files_frame, text="Select files to stage:").pack(anchor="w", pady=(0, 5))
            for line in changes:
                status = line[:2]
                filename = line[3:]
                var = BooleanVar()
                text = f"{status.strip():<2}  {filename}"
                chk = ttk.Checkbutton(files_frame, text=text, variable=var)
                chk.pack(anchor="w")
                file_vars[filename] = var
    except subprocess.CalledProcessError:
        ttk.Label(files_frame, text="Error loading files").pack(anchor="w")

def load_history(history_tree):
    global repo_path
    for row in history_tree.get_children():
        history_tree.delete(row)

    if not repo_path:
        return

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "--oneline", "-n", "10"],
            capture_output=True, text=True, check=True
        )
        commits = result.stdout.strip().splitlines()
        for commit in commits:
            parts = commit.split(" ", 1)
            if len(parts) == 2:
                sha, msg = parts
                tag = "default"
                for t in ["feat", "fix", "docs", "chore", "refactor", "style", "test", "perf"]:
                    if msg.startswith(t):
                        tag = t
                        break
                history_tree.insert("", "end", values=(sha, msg), tags=(tag,))
    except subprocess.CalledProcessError:
        history_tree.insert("", "end", values=("Error", "Could not load history"))