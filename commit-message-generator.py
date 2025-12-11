import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os

commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf"]
repo_path = None

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
        subprocess.run(["git", "-C", repo_path, "add", "."], check=True)
        subprocess.run(["git", "-C", repo_path, "commit", "-m", commit_msg], check=True)
        messagebox.showinfo("Success", f"Commit created successfully in {repo_path}!")
        check_changes()
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

# Main window
root = tk.Tk()
root.title("Commit Message Generator")

# Set fixed size
root.geometry("550x600")   # width x height
root.minsize(550, 600)     # prevent shrinking smaller
root.configure(bg="#2b2b2b")  # dark background

# Apply style
style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 10), padding=6, background="#3c3f41", foreground="white")
style.configure("TLabel", font=("Segoe UI", 10), background="#2b2b2b", foreground="white")
style.configure("TCheckbutton", background="#2b2b2b", foreground="white")

# Repo selector frame
repo_frame = ttk.LabelFrame(root, text="Repository", padding=10)
repo_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

ttk.Button(repo_frame, text="Choose Repo", command=choose_repo).grid(row=0, column=0, padx=5, pady=5)
repo_label = ttk.Label(repo_frame, text="Repo: None selected")
repo_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

# Commit details frame
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

# Preview frame
preview_frame = ttk.LabelFrame(root, text="Preview", padding=10)
preview_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

preview_text = tk.Text(preview_frame, height=5, width=60, bg="#1e1e1e", fg="white", insertbackground="white")
preview_text.pack(fill="both", expand=True)

# Status frame
status_frame = ttk.LabelFrame(root, text="Repo Status", padding=10)
status_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

status_label = ttk.Label(status_frame, text="Repo status: unknown")
status_label.pack(side="left", padx=5)

canvas = tk.Canvas(status_frame, width=20, height=20, bg="#2b2b2b", highlightthickness=0)
canvas.pack(side="right", padx=5)
light = canvas.create_oval(2, 2, 18, 18, fill="grey")

root.mainloop()