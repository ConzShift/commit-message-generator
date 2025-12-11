import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os

commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf"]
repo_path = None
file_vars = {}  # track checkboxes for files

def choose_repo():
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

def generate_commit():
    ctype = type_var.get()
    scope = scope_entry.get().strip()
    desc = desc_entry.get().strip()
    breaking = breaking_var.get()

    if not desc:
        messagebox.showerror("Error", "Description cannot be empty")
        return

    if scope:
        commit_msg = f"{ctype}({scope}): {desc}"
    else:
        commit_msg = f"{ctype}: {desc}"

    if breaking:
        commit_msg += f"\n\nBREAKING CHANGE: {desc}"

    preview_text.delete("1.0", tk.END)
    preview_text.insert(tk.END, commit_msg)

def commit_now():
    global repo_path
    commit_msg = preview_text.get("1.0", tk.END).strip()
    if not commit_msg:
        messagebox.showerror("Error", "No commit message generated")
        return
    if not repo_path:
        messagebox.showerror("Error", "No repository selected")
        return

    try:
        # Stage only selected files (if any)
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

def check_changes():
    global repo_path
    if not repo_path:
        status_label.config(text="Repo status: No repository selected")
        canvas.itemconfig(light, fill="grey")
        return
    
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "status", "--short"],
            capture_output=True, text=True, check=True
        )
        changes = result.stdout.strip()
        if not changes:
            status_label.config(text="Working tree clean (no changes)")
            canvas.itemconfig(light, fill="green")
        else:
            staged = subprocess.run(
                ["git", "-C", repo_path, "diff", "--cached", "--name-only"],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            if staged:
                status_label.config(text="Staged changes ready to commit")
                canvas.itemconfig(light, fill="red")
            else:
                status_label.config(text="Unstaged changes detected")
                canvas.itemconfig(light, fill="orange")
    except subprocess.CalledProcessError as e:
        status_label.config(text=f"Git Error: {e}")
        canvas.itemconfig(light, fill="grey")

def load_files():
    """List changed files with checkboxes for staging"""
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
                # Format: XY filename (e.g., " M file.py", "A  new.py", "?? untracked.txt")
                status = line[:2]
                filename = line[3:]
                var = tk.BooleanVar()
                text = f"{status.strip():<2}  {filename}"
                chk = ttk.Checkbutton(files_frame, text=text, variable=var)
                chk.pack(anchor="w")
                file_vars[filename] = var
    except subprocess.CalledProcessError:
        ttk.Label(files_frame, text="Error loading files").pack(anchor="w")

def load_history():
    """Show recent commits in a table"""
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
                # Tag rows by type for color highlighting
                tag = "default"
                if msg.startswith("feat"):
                    tag = "feat"
                elif msg.startswith("fix"):
                    tag = "fix"
                elif msg.startswith("docs"):
                    tag = "docs"
                elif msg.startswith("chore"):
                    tag = "chore"
                elif msg.startswith("refactor"):
                    tag = "refactor"
                elif msg.startswith("style"):
                    tag = "style"
                elif msg.startswith("test"):
                    tag = "test"
                elif msg.startswith("perf"):
                    tag = "perf"
                history_tree.insert("", "end", values=(sha, msg), tags=(tag,))
    except subprocess.CalledProcessError:
        history_tree.insert("", "end", values=("Error", "Could not load history"))

# Main window
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

# Repo selector
repo_frame = ttk.LabelFrame(root, text="Repository", padding=10)
repo_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
ttk.Button(repo_frame, text="Choose Repo", command=choose_repo).grid(row=0, column=0, padx=5, pady=5)
repo_label = ttk.Label(repo_frame, text="Repo: None selected")
repo_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

# Commit details
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
ttk.Button(commit_frame, text="Generate", command=generate_commit).grid(row=4, column=0, padx=5, pady=10)
ttk.Button(commit_frame, text="Commit Now", command=commit_now).grid(row=4, column=1, padx=5, pady=10)
ttk.Button(commit_frame, text="Check Changes", command=check_changes).grid(row=4, column=2, padx=5, pady=10)

# Preview
preview_frame = ttk.LabelFrame(root, text="Preview", padding=10)
preview_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
preview_text = tk.Text(preview_frame, height=5, width=80, bg="#1e1e1e", fg="white", insertbackground="white")
preview_text.pack(fill="both", expand=True)

# File selector
files_container = ttk.LabelFrame(root, text="Changed Files", padding=10)
files_container.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
# Make this section scrollable
files_scroll = ttk.Scrollbar(files_container, orient="vertical")
files_scroll.pack(side="right", fill="y")
files_frame = ttk.Frame(files_container)
files_frame.pack(fill="both", expand=True)
# Connect scrolling via canvas if needed; for simplicity, we rely on pack and scrollbar for future expansion

# Commit history
history_frame = ttk.LabelFrame(root, text="Recent Commits", padding=10)
history_frame.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky="nsew")
history_tree = ttk.Treeview(history_frame, columns=("sha", "msg"), show="headings", height=12)
history_tree.heading("sha", text="SHA")
history_tree.heading("msg", text="Message")
history_tree.column("sha", width=100, anchor="w")
history_tree.column("msg", width=500, anchor="w")
history_tree.pack(fill="both", expand=True)

# Tag styles for commit types
history_tree.tag_configure("feat", foreground="#6DD16A")     # green
history_tree.tag_configure("fix", foreground="#FF6B6B")      # red
history_tree.tag_configure("docs", foreground="#6CA0FF")     # blue
history_tree.tag_configure("chore", foreground="#C5C8C9")    # grey
history_tree.tag_configure("refactor", foreground="#F5A623") # orange
history_tree.tag_configure("style", foreground="#B084F5")    # purple
history_tree.tag_configure("test", foreground="#FFD166")     # yellow
history_tree.tag_configure("perf", foreground="#50E3C2")     # teal
history_tree.tag_configure("default", foreground="white")

# Status frame
status_frame = ttk.LabelFrame(root, text="Repo Status", padding=10)
status_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
status_label = ttk.Label(status_frame, text="Repo status: unknown")
status_label.pack(side="left", padx=5)
canvas = tk.Canvas(status_frame, width=20, height=20, bg="#2b2b2b", highlightthickness=0)
canvas.pack(side="right", padx=5)
light = canvas.create_oval(2, 2, 18, 18, fill="grey")

# Make grid responsive
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=1)  # files/history section expands

# Initial state
# Optionally auto-refresh status/history every few seconds:
def auto_refresh():
    if repo_path:
        check_changes()
        load_files()
        load_history()
    root.after(8000, auto_refresh)  # every 8 seconds
auto_refresh()

root.mainloop()