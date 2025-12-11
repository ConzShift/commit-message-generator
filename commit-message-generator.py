import tkinter as tk
from tkinter import ttk, messagebox
import subprocess

# Valid commit types
commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf"]

def generate_commit():
    ctype = type_var.get()
    scope = scope_entry.get().strip()
    desc = desc_entry.get().strip()
    breaking = breaking_var.get()

    if not desc:
        messagebox.showerror("Error", "Description cannot be empty")
        return

    # Build commit message
    if scope:
        commit_msg = f"{ctype}({scope}): {desc}"
    else:
        commit_msg = f"{ctype}: {desc}"

    if breaking:
        commit_msg += f"\n\nBREAKING CHANGE: {desc}"

    # Show preview
    preview_text.delete("1.0", tk.END)
    preview_text.insert(tk.END, commit_msg)

def commit_now():
    commit_msg = preview_text.get("1.0", tk.END).strip()
    if not commit_msg:
        messagebox.showerror("Error", "No commit message generated")
        return

    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        messagebox.showinfo("Success", "Commit created successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Git Error", f"Failed to commit: {e}")

# Main window
root = tk.Tk()
root.title("Commit Message Generator")

# Commit type dropdown
ttk.Label(root, text="Commit Type").grid(row=0, column=0, padx=5, pady=5, sticky="w")
type_var = tk.StringVar(value=commit_types[0])
ttk.Combobox(root, textvariable=type_var, values=commit_types).grid(row=0, column=1, padx=5, pady=5)

# Scope field
ttk.Label(root, text="Scope").grid(row=1, column=0, padx=5, pady=5, sticky="w")
scope_entry = ttk.Entry(root)
scope_entry.grid(row=1, column=1, padx=5, pady=5)

# Description field
ttk.Label(root, text="Description").grid(row=2, column=0, padx=5, pady=5, sticky="w")
desc_entry = ttk.Entry(root, width=40)
desc_entry.grid(row=2, column=1, padx=5, pady=5)

# Breaking change checkbox
breaking_var = tk.BooleanVar()
ttk.Checkbutton(root, text="Breaking Change", variable=breaking_var).grid(row=3, column=1, padx=5, pady=5, sticky="w")

# Buttons
ttk.Button(root, text="Generate", command=generate_commit).grid(row=4, column=0, padx=5, pady=10)
ttk.Button(root, text="Commit Now", command=commit_now).grid(row=4, column=1, padx=5, pady=10)

# Preview box
ttk.Label(root, text="Preview").grid(row=5, column=0, padx=5, pady=5, sticky="w")
preview_text = tk.Text(root, height=5, width=50)
preview_text.grid(row=6, column=0, columnspan=2, padx=5, pady=5)

root.mainloop()