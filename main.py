import tkinter as tk
from tkinter import ttk, messagebox
from git_utils import check_changes, load_files, load_history
from export_utils import export_summary
from ui_components import create_preview_box

def main():
    root = tk.Tk()
    root.title("Commit Generator")

    # Preview box
    preview = create_preview_box(root)
    preview.pack(fill="both", expand=True, padx=10, pady=10)

    # Buttons
    actions = ttk.Frame(root)
    actions.pack(fill="x", padx=10, pady=10)

    ttk.Button(actions, text="Check Changes", command=check_changes).grid(row=0, column=0, padx=5)
    ttk.Button(actions, text="Export Summary", command=export_summary).grid(row=0, column=1, padx=5)

    # Hotkeys
    root.bind("<Control-Return>", lambda e: print("Commit triggered"))
    root.bind("<Control-g>", lambda e: print("Generate commit"))
    root.bind("<Control-r>", lambda e: [check_changes(), load_files(), load_history()])

    root.mainloop()

if __name__ == "__main__":
    main()