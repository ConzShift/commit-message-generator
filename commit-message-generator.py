# app.py
import os
import re
import subprocess
import tkinter as tk
from tkinter import ttk
from datetime import datetime

# -----------------------------
# AI setup (graceful fallback)
# -----------------------------
generator = None
try:
    from transformers import pipeline
    # Load once at startup; you can swap model to "bigcode/starcoderbase"
    generator = pipeline(
        "text-generation",
        model="bigcode/santacoder",
        device=0  # set to -1 for CPU if no GPU
    )
except Exception:
    generator = None  # Will fallback to rule-based suggestion

# -----------------------------
# Repo helpers (git_utils)
# -----------------------------
class GitUtils:
    repo_path = ""

    @staticmethod
    def choose_repo(repo_label, on_status, on_files, on_history):
        # Simple folder picker
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select Git repository")
        if not path:
            return
        GitUtils.repo_path = path
        repo_label.config(text=f"Repo: {path}")
        # Ensure it's a git repo
        if not os.path.isdir(os.path.join(path, ".git")):
            GitUtils.repo_path = ""
            repo_label.config(text="Repo: ⚠️ Not a git repository")
            return
        # Refresh UI
        on_status()
        on_files()
        on_history()

    @staticmethod
    def _git_cmd(args):
        if not GitUtils.repo_path:
            return subprocess.CompletedProcess(args, 1, "", "No repo selected")
        return subprocess.run(
            args,
            cwd=GitUtils.repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            shell=False
        )

    @staticmethod
    def check_changes(status_label, canvas, light):
        # Show if there are staged/unstaged changes
        diff_unstaged = GitUtils._git_cmd(["git", "diff"]).stdout.strip()
        diff_staged = GitUtils._git_cmd(["git", "diff", "--staged"]).stdout.strip()
        if diff_unstaged or diff_staged:
            status_label.config(text="Repo status: changes detected")
            canvas.itemconfig(light, fill="orange")
        else:
            status_label.config(text="Repo status: clean")
            canvas.itemconfig(light, fill="green")

    @staticmethod
    def load_files(files_frame):
        # Clear frame
        for w in files_frame.winfo_children():
            w.destroy()
        # List changed files
        result = GitUtils._git_cmd(["git", "status", "--porcelain"])
        lines = result.stdout.splitlines()
        if not lines:
            ttk.Label(files_frame, text="No changed files").pack(anchor="w")
            return
        for line in lines:
            ttk.Label(files_frame, text=line).pack(anchor="w")

    @staticmethod
    def load_history(history_tree):
        # Clear existing
        for item in history_tree.get_children():
            history_tree.delete(item)
        result = GitUtils._git_cmd(["git", "log", "--pretty=format:%h|%s", "-n", "20"])
        for row in result.stdout.splitlines():
            if "|" in row:
                sha, msg = row.split("|", 1)
                history_tree.insert("", "end", values=(sha, msg))

git_utils = GitUtils  # alias for consistency

# -----------------------------
# Export helpers (export_utils)
# -----------------------------
def export_summary(repo_path):
    if not repo_path:
        return
    result = subprocess.run(
        ["git", "log", "--pretty=format:%h %an %ad %s", "--date=short", "-n", "100"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    out = result.stdout
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = os.path.join(repo_path, f"commit-history-{ts}.txt")
    with open(fname, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Exported history to {fname}")

# -----------------------------
# Commit helpers (commit_utils)
# -----------------------------
def build_conventional_message(commit_type, scope, description, breaking=False):
    scope_part = f"({scope})" if scope.strip() else ""
    bang = "!" if breaking else ""
    return f"{commit_type}{scope_part}{bang}: {description}".strip()

def generate_commit(type_var, scope_entry, desc_entry, breaking_var, preview_widget):
    commit_type = type_var.get()
    scope = scope_entry.get().strip()
    description = desc_entry.get().strip()
    breaking = bool(breaking_var.get())

    msg = build_conventional_message(commit_type, scope, description, breaking)
    preview_widget.config(state="normal")
    preview_widget.delete("1.0", "end")
    preview_widget.insert("end", msg)
    preview_widget.config(state="disabled")

def commit_now(repo_path, preview_widget, file_vars=None, on_status=None, on_files=None, on_history=None, status_label=None):
    if not repo_path:
        return
    # Read preview text
    preview_widget.config(state="normal")
    msg = preview_widget.get("1.0", "end").strip()
    preview_widget.config(state="disabled")
    if not msg:
        msg = "chore: update project files"

    # Stage all and commit
    subprocess.run(["git", "add", "-A"], cwd=repo_path)
    subprocess.run(["git", "commit", "-m", msg], cwd=repo_path)

    # Refresh UI
    if on_status: on_status()
    if on_files: on_files()
    if on_history: on_history()
    if status_label: status_label.config(text="✅ Commit completed", foreground="green")

# -----------------------------
# AI suggestion (ai_utils)
# -----------------------------
def get_recent_commits(repo_path, n=10):
    if not repo_path:
        return ""
    result = subprocess.run(
        ["git", "log", "--pretty=format:%s", "-n", str(n)],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    return result.stdout

def suggest_commit_message(diff_text: str, style_examples: str = "") -> str:
    # If no generator, fallback to rule-based guess
    if generator is None:
        # Simple heuristic
        lower = diff_text.lower()
        if "fix" in lower or "bug" in lower or "error" in lower:
            base = "fix"
        elif "test" in lower or "assert" in lower:
            base = "test"
        elif "perf" in lower or "optimiz" in lower:
            base = "perf"
        elif "doc" in lower or "readme" in lower:
            base = "docs"
        elif "refactor" in lower or "cleanup" in lower:
            base = "refactor"
        elif "style" in lower or "lint" in lower or "format" in lower:
            base = "style"
        elif "dependenc" in lower or "version" in lower:
            base = "chore"
        else:
            base = "feat"
        return f"{base}: update based on staged diff"

    # Strong prompt with examples
    prompt = (
        (f"Here are recent commit messages to match style:\n{style_examples}\n\n" if style_examples else "")
        + "Write a Conventional Commit message (feat, fix, docs, style, refactor, test, chore, perf) "
          "summarizing the following diff:\n"
        + diff_text
        + "\nMessage:"
    )

    try:
        result = generator(
            prompt,
            max_new_tokens=50,
            truncation=True,
            do_sample=True,
            temperature=0.6,
            top_p=0.9
        )
        suggestion = result[0]["generated_text"]
        if "Message:" in suggestion:
            suggestion = suggestion.split("Message:")[-1].strip()
        # Allow typical commit punctuation
        suggestion = re.sub(r'[^a-zA-Z0-9\s:._-]', '', suggestion).strip()
        # Sanity: ensure it starts with a type; if not, prepend feat:
        if not re.match(r'^(feat|fix|docs|style|refactor|test|chore|perf)\s*:?', suggestion):
            suggestion = f"feat: {suggestion}" if suggestion else "chore: update project files"
        return suggestion or "chore: update project files"
    except Exception:
        return "chore: update project files"

# -----------------------------
# UI setup
# -----------------------------
commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf"]

root = tk.Tk()
root.title("Commit Message Generator")
root.geometry("1100x800")
root.minsize(1100, 800)
root.configure(bg="#2b2b2b")

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 10), padding=6, background="#3f4f59", foreground="white")
style.configure("TLabel", font=("Segoe UI", 10), background="#2b2b2b", foreground="white")
style.configure("TCheckbutton", background="#2b2b2b", foreground="white")
style.configure("TLabelframe", background="#2b2b2b", foreground="white")
style.configure("TLabelframe.Label", background="#2b2b2b", foreground="white")

# Responsive layout
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(2, weight=1)  # Preview row
root.grid_rowconfigure(3, weight=1)  # Files and history row

# Repository
repo_frame = ttk.LabelFrame(root, text="Repository", padding=10)
repo_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

ttk.Button(
    repo_frame, text="Choose Repo",
    command=lambda: git_utils.choose_repo(
        repo_label,
        lambda: git_utils.check_changes(status_label, canvas, light),
        lambda: git_utils.load_files(files_frame),
        lambda: git_utils.load_history(history_tree)
    )
).grid(row=0, column=0, padx=5, pady=5)

repo_label = ttk.Label(repo_frame, text="Repo:")
repo_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

repo_status_label = ttk.Label(repo_frame, text="⚠️ No repository selected", foreground="orange")
repo_status_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

ttk.Button(repo_frame, text="Export History",
           command=lambda: export_summary(git_utils.repo_path)).grid(row=0, column=3, padx=5, pady=5)

# Commit details
import tkinter as tk
from tkinter import ttk

# Import helper modules
import git_utils
from commit_utils import generate_commit, commit_now
from export_utils import export_summary

commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf"]

# --- Main window setup ---
root = tk.Tk()
root.title("Commit Message Generator")
root.geometry("900x750")
root.minsize(900, 750)
root.configure(bg="#2b2b2b")

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 10), padding=6, background="#3c3f41", foreground="white")
style.configure("TLabel", font=("Segoe UI", 10), background="#2b2b2b", foreground="white")
style.configure("TCheckbutton", background="#2b2b2b", foreground="white")
style.configure("TLabelframe", background="#2b2b2b", foreground="white")
style.configure("TLabelframe.Label", background="#2b2b2b", foreground="white")

# --- Repo selector ---
repo_frame = ttk.LabelFrame(root, text="Repository", padding=10)
repo_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

# Choose Repo button
ttk.Button(repo_frame, text="Choose Repo",
           command=lambda: git_utils.choose_repo(
               repo_label,
               lambda: git_utils.check_changes(status_label, canvas, light),
               lambda: git_utils.load_files(files_frame),
               lambda: git_utils.load_history(history_tree))
           ).grid(row=0, column=0, padx=5, pady=5)

# Repo label
repo_label = ttk.Label(repo_frame, text="Repo:")
repo_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

# Status reminder label (next to Choose Repo button)
repo_status_label = ttk.Label(repo_frame, text="⚠️ No repository selected", foreground="orange")
repo_status_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

# Export History button
ttk.Button(repo_frame, text="Export History",
           command=lambda: export_summary(git_utils.repo_path)).grid(row=0, column=3, padx=5, pady=5)

# --- Commit details ---
commit_frame = ttk.LabelFrame(root, text="Commit Details", padding=10)
commit_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

ttk.Label(commit_frame, text="Commit Type").grid(row=0, column=0, padx=5, pady=5, sticky="w")
type_var = tk.StringVar(value=commit_types[0])
ttk.Combobox(commit_frame, textvariable=type_var, values=commit_types).grid(row=0, column=1, padx=5, pady=5)

ttk.Label(commit_frame, text="Scope").grid(row=1, column=0, padx=5, pady=5, sticky="w")
scope_entry = ttk.Entry(commit_frame)
scope_entry.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(commit_frame, text="Description").grid(row=2, column=0, padx=5, pady=5, sticky="w")
desc_entry = ttk.Entry(commit_frame, width=40)
desc_entry.grid(row=2, column=1, padx=5, pady=5)

breaking_var = tk.BooleanVar()
ttk.Checkbutton(commit_frame, text="Breaking Change", variable=breaking_var).grid(row=3, column=1, padx=5, pady=5, sticky="w")

ttk.Button(commit_frame, text="Generate",
           command=lambda: generate_commit(type_var, scope_entry, desc_entry, breaking_var, preview_text)
           ).grid(row=4, column=0, padx=5, pady=10)

ttk.Button(commit_frame, text="Commit Now",
           command=lambda: commit_now(
               git_utils.repo_path, preview_text, None,
               lambda: git_utils.check_changes(status_label, canvas, light),
               lambda: git_utils.load_files(files_frame),
               lambda: git_utils.load_history(history_tree),
               repo_status_label
           )
           ).grid(row=4, column=1, padx=5, pady=10)

ttk.Button(commit_frame, text="Suggest with AI",
           command=lambda: preview_ai_suggestion(preview_text)
           ).grid(row=4, column=2, padx=5, pady=10)

# Preview
preview_frame = ttk.LabelFrame(root, text="Preview", padding=10)
preview_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
preview_frame.grid_rowconfigure(0, weight=1)
preview_frame.grid_columnconfigure(0, weight=1)

preview_text = tk.Text(preview_frame, height=5, width=80,
                       bg="#1e1e1e", fg="white", insertbackground="white", wrap="word")
preview_text.grid(row=0, column=0, sticky="nsew")
preview_text.config(state="disabled")

# Files
files_container = ttk.LabelFrame(root, text="Changed Files", padding=10)
files_container.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
files_frame = ttk.Frame(files_container)
files_frame.pack(fill="both", expand=True)

# History
history_frame = ttk.LabelFrame(root, text="Recent Commits", padding=10)
history_frame.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky="nsew")
history_tree = ttk.Treeview(history_frame, columns=("sha", "msg"), show="headings", height=12)
history_tree.heading("sha", text="SHA")
history_tree.heading("msg", text="Message")
history_tree.column("sha", width=100, anchor="w")
history_tree.column("msg", width=500, anchor="w")
history_tree.pack(fill="both", expand=True)

# Status
status_frame = ttk.LabelFrame(root, text="Repo Status", padding=10)
status_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
status_label = ttk.Label(status_frame, text="Repo status: unknown")
status_label.pack(side="left", padx=5)
canvas = tk.Canvas(status_frame, width=20, height=20, bg="#2b2b2b", highlightthickness=0)
canvas.pack(side="right", padx=5)
light = canvas.create_oval(2, 2, 18, 18, fill="grey")

# Auto refresh
def auto_refresh():
    if git_utils.repo_path:
        git_utils.check_changes(status_label, canvas, light)
        git_utils.load_files(files_frame)
        git_utils.load_history(history_tree)
        repo_status_label.config(text="✅ Repository ready", foreground="green")
    else:
        repo_status_label.config(text="⚠️ No repository selected", foreground="orange")
    root.after(8000, auto_refresh)

auto_refresh()

# AI preview helper
def preview_ai_suggestion(preview_widget):
    if not git_utils.repo_path:
        suggestion = "⚠️ No repository selected."
    else:
        subprocess.run(["git", "add", "-A"], cwd=git_utils.repo_path)
        result = subprocess.run(
            ["git", "diff", "--staged"],
            cwd=git_utils.repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        diff_text = result.stdout
        if not diff_text.strip():
            suggestion = "⚠️ No changes found in repo."
        else:
            history_examples = get_recent_commits(git_utils.repo_path, n=10)
            suggestion = suggest_commit_message(diff_text, style_examples=history_examples)

    preview_widget.config(state="normal")
    preview_widget.delete("1.0", "end")
    preview_widget.insert("end", f"AI Suggestion:\n{suggestion}")
    preview_widget.config(state="disabled")

# Hotkeys
root.bind("<Control-Return>", lambda e: commit_now(
    git_utils.repo_path, preview_text, None,
    lambda: git_utils.check_changes(status_label, canvas, light),
    lambda: git_utils.load_files(files_frame),
    lambda: git_utils.load_history(history_tree),
    repo_status_label
))
root.bind("<Control-g>", lambda e: generate_commit(type_var, scope_entry, desc_entry, breaking_var, preview_text))
root.bind("<Control-r>", lambda e: [
    git_utils.check_changes(status_label, canvas, light),
    git_utils.load_files(files_frame),
    git_utils.load_history(history_tree)
])
root.bind("<Control-o>", lambda e: git_utils.choose_repo(
    repo_label,
    lambda: git_utils.check_changes(status_label, canvas, light),
    lambda: git_utils.load_files(files_frame),
    lambda: git_utils.load_history(history_tree)
))

root.mainloop()
print("App reached the end of the script.")
