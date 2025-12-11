from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from tkinter import messagebox
import subprocess

def export_summary(repo_path):
    if not repo_path:
        messagebox.showerror("Error", "No repository selected")
        return

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "--pretty=format:%h|%s|%cI", "-n", "20"],
            capture_output=True, text=True, check=True
        )
        commits = result.stdout.strip().splitlines()

        width, height = 1000, 60 + len(commits) * 60
        img = Image.new("RGB", (width, height), "#2b2b2b")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        draw.text((20, 20), f"Commit Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill="white", font=font)

        y = 60
        for line in commits:
            sha, msg, date = line.split("|", 2)
            color = "#6DD16A" if msg.startswith("feat") else "#FF6B6B" if msg.startswith("fix") else "white"
            draw.text((40, y), f"{sha}", fill=color, font=font)
            draw.text((120, y), f"{msg}", fill="white", font=font)
            draw.text((700, y), f"{date}", fill="#aaaaaa", font=font)
            y += 40

        img.save("commit_summary.png")

        pdf = pdf_canvas.Canvas("commit_summary.pdf", pagesize=A4)
        pdf.drawImage("commit_summary.png", 50, 400, width=500, preserveAspectRatio=True)
        pdf.save()

        messagebox.showinfo("Export Complete", "Saved commit_summary.png and commit_summary.pdf")
    except Exception as e:
        messagebox.showerror("Export Error", str(e))