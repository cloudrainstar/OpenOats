#!/usr/bin/env python3
import queue
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ots.kb import KB
from ots.logic import suggest
from ots.mac_overlay import tune_tk_overlay_for_macos
from ots.mic import stream_mic_chunks
from ots.settings import load_settings, save_settings
from ots.storage import SessionStore
from ots.stt import Transcriber
from ots.ui_theme import apply_theme


class OTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("On The Spot")
        self.root.geometry("1160x780")
        self.root.minsize(980, 620)

        self.colors = apply_theme(root)
        self.settings = load_settings()

        self.store = SessionStore(enabled=True)
        self.kb = None
        self.q = queue.Queue()
        self.running = False
        self.stop_event = threading.Event()

        self.overlay = None
        self.overlay_text = None
        self.overlay_visible = tk.BooleanVar(value=bool(self.settings.get("overlay_enabled", False)))
        self.clickthrough_var = tk.BooleanVar(value=bool(self.settings.get("clickthrough", False)))

        self.audio_var = tk.StringVar(value=self.settings.get("last_audio", ""))
        self.kb_var = tk.StringVar(value=self.settings.get("kb_path", ""))
        self.model_var = tk.StringVar(value=self.settings.get("model", "small"))
        self.backend_var = tk.StringVar(value=self.settings.get("backend", "auto"))
        self.threads_var = tk.IntVar(value=int(self.settings.get("threads", 4)))
        self.status_var = tk.StringVar(value="Idle")
        self.mode_var = tk.StringVar(value="file")

        self._build_ui()
        self._first_run_wizard()

        self.root.bind("<Escape>", lambda e: self.hide_overlay())
        self.root.bind("<Control-Shift-O>", lambda e: self.toggle_overlay())
        self.root.after(150, self._poll)

    def _build_ui(self):
        rootf = ttk.Frame(self.root, style="Root.TFrame")
        rootf.pack(fill="both", expand=True, padx=14, pady=14)

        hdr = ttk.Frame(rootf, style="Root.TFrame")
        hdr.pack(fill="x", pady=(0, 10))
        ttk.Label(hdr, text="On The Spot", style="Title.TLabel").pack(side="left")
        ttk.Label(hdr, text="Meeting copilot", style="Muted.TLabel").pack(side="left", padx=10)
        ttk.Label(hdr, textvariable=self.status_var, style="Muted.TLabel").pack(side="right")

        controls = ttk.Frame(rootf, style="Panel.TFrame", padding=12)
        controls.pack(fill="x")

        ttk.Label(controls, text="Mode").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(controls, text="Audio File", variable=self.mode_var, value="file").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(controls, text="Live Mic", variable=self.mode_var, value="mic").grid(row=0, column=2, sticky="w")

        ttk.Label(controls, text="Audio File").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.audio_var, width=76).grid(row=1, column=1, sticky="we", padx=8, pady=(8, 0), columnspan=2)
        ttk.Button(controls, text="Browse", command=self.pick_audio).grid(row=1, column=3, pady=(8, 0))

        ttk.Label(controls, text="Knowledge Base").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.kb_var, width=76).grid(row=2, column=1, sticky="we", padx=8, pady=(8, 0), columnspan=2)
        ttk.Button(controls, text="Browse", command=self.pick_kb).grid(row=2, column=3, pady=(8, 0))

        ttk.Label(controls, text="Backend").grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.OptionMenu(controls, self.backend_var, self.backend_var.get(), "auto", "faster-whisper", "mlx-whisper").grid(row=3, column=1, sticky="w", pady=(10, 0))
        ttk.Label(controls, text="Model").grid(row=3, column=2, sticky="e", pady=(10, 0))
        ttk.Entry(controls, textvariable=self.model_var, width=16).grid(row=3, column=3, sticky="w", pady=(10, 0))

        ttk.Label(controls, text="Threads").grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(controls, from_=1, to=16, textvariable=self.threads_var, width=8).grid(row=4, column=1, sticky="w", pady=(10, 0))

        controls.columnconfigure(1, weight=1)

        actions = ttk.Frame(rootf, style="Root.TFrame")
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="Start Meeting Mode", command=self.start_meeting_mode, style="Accent.TButton").pack(side="left")
        ttk.Button(actions, text="Stop", command=self.stop).pack(side="left", padx=8)
        ttk.Button(actions, text="Settings", command=self.open_settings).pack(side="left", padx=8)
        ttk.Button(actions, text="Verify Invisibility", command=self.verify_invisibility).pack(side="left", padx=8)
        ttk.Button(actions, text="Open Sessions", command=self.open_sessions).pack(side="left", padx=8)
        ttk.Checkbutton(actions, text="Overlay", variable=self.overlay_visible, command=self.toggle_overlay).pack(side="left", padx=10)
        ttk.Checkbutton(actions, text="Click-through", variable=self.clickthrough_var, command=self.apply_clickthrough).pack(side="left", padx=2)
        ttk.Label(actions, text="Esc: hide overlay  •  Ctrl+Shift+O: toggle", style="Muted.TLabel").pack(side="right")

        panes = ttk.PanedWindow(rootf, orient="horizontal")
        panes.pack(fill="both", expand=True)

        left = ttk.Frame(panes, style="Panel.TFrame", padding=10)
        right = ttk.Frame(panes, style="Panel.TFrame", padding=10)
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        ttk.Label(left, text="Transcript").pack(anchor="w")
        self.transcript = tk.Text(left, wrap="word", bg="#0d1016", fg="#e7eaf0", insertbackground="#e7eaf0", relief="flat")
        self.transcript.pack(fill="both", expand=True, pady=(6, 0))

        ttk.Label(right, text="Suggestions").pack(anchor="w")
        self.suggestions = tk.Text(right, wrap="word", bg="#0d1016", fg="#e7eaf0", insertbackground="#e7eaf0", relief="flat")
        self.suggestions.pack(fill="both", expand=True, pady=(6, 0))

    def _first_run_wizard(self):
        if Path("data/settings.json").exists():
            return
        messagebox.showinfo("Welcome", "Let’s do quick setup: choose KB folder and preferred backend/model.")
        kb = filedialog.askdirectory(title="Choose Knowledge Base folder (optional)")
        if kb:
            self.kb_var.set(kb)
        self.persist_settings()

    def persist_settings(self):
        self.settings.update({
            "backend": self.backend_var.get(),
            "model": self.model_var.get(),
            "kb_path": self.kb_var.get().strip(),
            "last_audio": self.audio_var.get().strip(),
            "overlay_enabled": bool(self.overlay_visible.get()),
            "clickthrough": bool(self.clickthrough_var.get()),
            "threads": int(self.threads_var.get()),
        })
        save_settings(self.settings)

    def open_settings(self):
        self.persist_settings()
        messagebox.showinfo("Settings", "Saved.\nThese defaults load automatically next launch.")

    def _ensure_overlay(self):
        if self.overlay is not None:
            return
        self.overlay = tk.Toplevel(self.root)
        self.overlay.title("On The Spot Overlay")
        self.overlay.geometry("450x280+36+56")
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg="#11131a")
        self.overlay.protocol("WM_DELETE_WINDOW", self.hide_overlay)

        frame = tk.Frame(self.overlay, bg="#11131a")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(frame, text="On The Spot", fg="#f2f4f8", bg="#11131a", font=("SF Pro Display", 14, "bold")).pack(anchor="w")
        tk.Label(frame, text="Private overlay (Esc to hide)", fg="#9aa4b2", bg="#11131a").pack(anchor="w", pady=(0, 8))
        self.overlay_text = tk.Text(frame, wrap="word", bg="#0b0e13", fg="#f2f4f8", insertbackground="#f2f4f8", relief="flat")
        self.overlay_text.pack(fill="both", expand=True)

        tune_tk_overlay_for_macos(self.overlay)
        self.overlay.withdraw()

    def toggle_overlay(self):
        self._ensure_overlay()
        if self.overlay_visible.get():
            self.overlay.deiconify()
            self.overlay.lift()
        else:
            self.overlay.withdraw()
        self.persist_settings()

    def hide_overlay(self):
        self.overlay_visible.set(False)
        if self.overlay is not None:
            self.overlay.withdraw()
        self.persist_settings()

    def apply_clickthrough(self):
        if self.overlay is None:
            return
        try:
            self.overlay.attributes("-alpha", 0.74 if self.clickthrough_var.get() else 1.0)
        except Exception:
            pass
        self.persist_settings()

    def pick_audio(self):
        p = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac")])
        if p:
            self.audio_var.set(p)
            self.persist_settings()

    def pick_kb(self):
        p = filedialog.askdirectory()
        if p:
            self.kb_var.set(p)
            self.persist_settings()

    def start_meeting_mode(self):
        if self.running:
            return
        mode = self.mode_var.get()
        if mode == "file" and not self.audio_var.get().strip():
            messagebox.showerror("Missing audio", "Pick an audio file or switch to Live Mic")
            return
        self.kb = KB(self.kb_var.get().strip() or None)
        self.running = True
        self.stop_event.clear()
        self.persist_settings()
        self.status_var.set(f"Running ({mode})…")
        self.transcript.insert("end", f"\n--- Session {datetime.now().strftime('%H:%M:%S')} [{mode}] ---\n")
        threading.Thread(target=self._worker, args=(mode,), daemon=True).start()

    def stop(self):
        self.stop_event.set()
        self.status_var.set("Stopping…")

    def _worker(self, mode: str):
        stt = Transcriber(self.backend_var.get(), self.model_var.get(), "int8", int(self.threads_var.get()))
        try:
            if mode == "file":
                for text in stt.transcribe_path(self.audio_var.get().strip()):
                    if self.stop_event.is_set():
                        break
                    self._handle_text(text)
            else:
                for chunk_path in stream_mic_chunks(4.0, 16000):
                    if self.stop_event.is_set():
                        break
                    for text in stt.transcribe_path(chunk_path):
                        if self.stop_event.is_set():
                            break
                        self._handle_text(text, speaker="YOU")
        finally:
            self.q.put(("__DONE__", [], []))

    def _handle_text(self, text: str, speaker: str = "OTHER"):
        ts = datetime.now(timezone.utc).isoformat()
        ctx = self.kb.search(text) if self.kb else []
        pts = suggest(text, ctx)
        self.store.append({"type": "turn", "ts": ts, "speaker": speaker, "text": text, "context": ctx, "suggestions": pts})
        self.q.put((text, pts, ctx))

    def _poll(self):
        try:
            while True:
                text, pts, _ctx = self.q.get_nowait()
                if text == "__DONE__":
                    self.transcript.insert("end", "\n[done]\n")
                    self.transcript.see("end")
                    self.status_var.set("Idle")
                    self.running = False
                    continue

                self.transcript.insert("end", f"\n• {text}\n")
                self.transcript.see("end")
                self.suggestions.insert("end", f"\nFor: {text[:90]}\n")
                for p in pts:
                    self.suggestions.insert("end", f"  • {p}\n")
                self.suggestions.see("end")

                if self.overlay_text is not None and self.overlay_visible.get():
                    self.overlay_text.delete("1.0", "end")
                    self.overlay_text.insert("end", f"Now\n{text[:240]}\n\nTalk track\n")
                    for p in pts:
                        self.overlay_text.insert("end", f"• {p}\n")
        except queue.Empty:
            pass
        self.root.after(150, self._poll)

    def verify_invisibility(self):
        self._ensure_overlay()
        self.overlay_visible.set(True)
        self.toggle_overlay()
        checklist = (
            "Invisibility Verification\n\n"
            "1) Start a screen share in Zoom/Meet/Teams.\n"
            "2) Share ENTIRE SCREEN: check if overlay appears to remote viewers.\n"
            "3) Share APP WINDOW only: confirm overlay is hidden from shared feed.\n"
            "4) Toggle overlay with Ctrl+Shift+O and test again.\n"
            "5) Press Esc (panic hide) and confirm immediate disappearance.\n\n"
            "If overlay is visible remotely in step 2, use window-share mode or keep panic hotkey ready."
        )
        messagebox.showinfo("Verify Invisibility", checklist)

    def open_sessions(self):
        p = Path("data/sessions").resolve()
        messagebox.showinfo("Sessions", f"Saved in: {p}")


def main():
    root = tk.Tk()
    OTSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
