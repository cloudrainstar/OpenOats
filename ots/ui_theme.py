from tkinter import ttk


def apply_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    bg = "#0f1117"
    panel = "#161a22"
    text = "#e6e8ee"
    muted = "#98a2b3"
    accent = "#7c5cff"

    root.configure(bg=bg)

    style.configure("Root.TFrame", background=bg)
    style.configure("Panel.TFrame", background=panel)
    style.configure("TLabel", background=bg, foreground=text)
    style.configure("Muted.TLabel", background=bg, foreground=muted)
    style.configure("Title.TLabel", background=bg, foreground=text, font=("SF Pro Display", 16, "bold"))
    style.configure("TButton", padding=8)
    style.map("Accent.TButton", background=[("!disabled", accent)], foreground=[("!disabled", "#ffffff")])

    return {"bg": bg, "panel": panel, "text": text, "muted": muted, "accent": accent}
