import tkinter as tk

def create_preview_box(root):
    preview = tk.Text(root, height=10, wrap="word", state="disabled", bg="#f9f9f9")
    return preview