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

repo_label = ttk.Label(repo_frame, text="Repo: None selected")
repo_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

ttk.Button(repo_frame, text="Choose Repo",
           command=lambda: git_utils.choose_repo(
               repo_label,
               lambda: git_utils.check_changes(status_label, canvas, light),
               lambda: git_utils.load_files(files_frame),
               lambda: git_utils.load_history(history_tree))
           ).grid(row=0, column=0, padx=5, pady=5)

ttk.Button(repo_frame, text="Export History",
           command=lambda: export_summary(git_utils.repo_path)).grid(row=0, column=2, padx=5, pady=5)

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
           command=lambda: generate_commit(type_var, scope_entry, desc_entry, breaking_var, preview_text)).grid(row=4, column=0, padx=5, pady=10)

ttk.Button(commit_frame, text="Commit Now",
           command=lambda: commit_now(git_utils.repo_path, preview_text, git_utils.file_vars,
                                      lambda: git_utils.check_changes(status_label, canvas, light),
                                      lambda: git_utils.load_files(files_frame),
                                      lambda: git_utils.load_history(history_tree))
           ).grid(row=4, column=1, padx=5, pady=10)

# --- Preview ---
preview_frame = ttk.LabelFrame(root, text="Preview", padding=10)
preview_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

preview_text = tk.Text(preview_frame, height=5, width=80,
                       bg="#1e1e1e", fg="white", insertbackground="white", wrap="word")
preview_text.pack(fill="both", expand=True)
preview_text.config(state="disabled")

# --- Files ---
files_container = ttk.LabelFrame(root, text="Changed Files", padding=10)
files_container.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
files_frame = ttk.Frame(files_container)
files_frame.pack(fill="both", expand=True)

# --- History ---
history_frame = ttk.LabelFrame(root, text="Recent Commits", padding=10)
history_frame.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky="nsew")
history_tree = ttk.Treeview(history_frame, columns=("sha", "msg"), show="headings", height=12)
history_tree.heading("sha", text="SHA")
history_tree.heading("msg", text="Message")
history_tree.column("sha", width=100, anchor="w")
history_tree.column("msg", width=500, anchor="w")
history_tree.pack(fill="both", expand=True)

# --- Status ---
status_frame = ttk.LabelFrame(root, text="Repo Status", padding=10)
status_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
status_label = ttk.Label(status_frame, text="Repo status: unknown")
status_label.pack(side="left", padx=5)
canvas = tk.Canvas(status_frame, width=20, height=20, bg="#2b2b2b", highlightthickness=0)
canvas.pack(side="right", padx=5)
light = canvas.create_oval(2, 2, 18, 18, fill="grey")

# --- Grid responsiveness ---
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=1)

# --- Auto refresh ---
def auto_refresh():
    if git_utils.repo_path:
        git_utils.check_changes(status_label, canvas, light)
        git_utils.load_files(files_frame)
        git_utils.load_history(history_tree)
    root.after(8000, auto_refresh)

auto_refresh()

# --- Hotkeys ---
root.bind("<Control-Return>", lambda e: commit_now(git_utils.repo_path, preview_text, git_utils.file_vars,
                                                   lambda: git_utils.check_changes(status_label, canvas, light),
                                                   lambda: git_utils.load_files(files_frame),
                                                   lambda: git_utils.load_history(history_tree)))
root.bind("<Control-g>", lambda e: generate_commit(type_var, scope_entry, desc_entry, breaking_var, preview_text))
root.bind("<Control-r>", lambda e: [git_utils.check_changes(status_label, canvas, light),
                                    git_utils.load_files(files_frame),
                                    git_utils.load_history(history_tree)])
root.bind("<Control-o>", lambda e: git_utils.choose_repo(repo_label,
                                                         lambda: git_utils.check_changes(status_label, canvas, light),
                                                         lambda: git_utils.load_files(files_frame),
                                                         lambda: git_utils.load_history(history_tree)))

root.mainloop()