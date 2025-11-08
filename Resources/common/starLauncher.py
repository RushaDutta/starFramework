import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import random
from datetime import datetime
import logging

class STAR(tk.Tk):
    def __init__(self, session_id, session_folder):
        super().__init__()
        self.title("STAR")
        self.geometry("700x500")
        self.resizable(False, False)
        self.session_id = session_id
        self.session_folder = session_folder

        # Header container: properly centers the STAR name and sets session to top right
        topbar = ttk.Frame(self)
        topbar.pack(fill="x", pady=(10, 8))

        self.title_label = ttk.Label(
            topbar,
            text="(S)takeholders, (T)ransparency, (A)I-parseable, (R)eflexive",
            foreground="#1d20d6",
            font=("Segoe UI", 14, "bold")
        )
        self.title_label.pack(side="top", pady=0)

        self.session_label = ttk.Label(
            topbar,
            text=f"Session: {self.session_id}",
            foreground="#0066CC",
            font=("Segoe UI", 10, "italic")
        )
        self.session_label.pack(side="right", padx=10, anchor="ne")

        # Main content
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Status label
        self.msg = ttk.Label(
            main_frame,
            text="Ready",
            wraplength=640,
            justify="center"
        )
        self.msg.pack(pady=(28, 12))

        # Finalize/workshop button
        self.btn_finalize = ttk.Button(
            main_frame,
            text="Launch STAR Workshop tool",
            command=self.finalize
        )
        self.btn_finalize.pack(pady=6, fill="x")

        # HTML viewer button
        self.btn_html = ttk.Button(
            main_frame,
            text="View Decision Cards",
            command=self.launch_html,
            state=tk.DISABLED
        )
        self.btn_html.pack(pady=6, fill="x")

        # Reflexive Summary viewer button
        self.btn_summary = ttk.Button(
            main_frame,
            text="View Reflexive Cycle Summary",
            command=self.launch_summary,
            state=tk.DISABLED
        )
        self.btn_summary.pack(pady=6, fill="x")

        # Status line
        self.progress = ttk.Label(
            main_frame,
            text="",
            foreground="#999999"
        )
        self.progress.pack(pady=(12, 0))

        # Paths to files
        self.result_path = ""
        self.html_path = ""
        self.summary_path = ""

    def finalize(self):
        self.session_label.config(text=f"Session: {self.session_id}")
        self.msg.config(text="Launching collaboration tool for input...\n")
        self.progress.config(text="")
        self.btn_finalize.config(state=tk.DISABLED)
        self.btn_html.config(state=tk.DISABLED)
        self.btn_summary.config(state=tk.DISABLED)
        threading.Thread(target=self.llm_workflow, daemon=True).start()
        self.animate_progress()

    def animate_progress(self):
        def animate():
            dots = ""
            while self.btn_finalize["state"] == tk.DISABLED:
                dots += "."
                if len(dots) > 4:
                    dots = ""
                self.progress.config(text=f"Processing{dots}")
                time.sleep(0.6)
        threading.Thread(target=animate, daemon=True).start()

    def llm_workflow(self):
        self.update_status("Waiting for feature data input (collaboration tool)...")
        try:
            features_path = os.path.join(self.session_folder, "workshop_output")
            collab_proc = subprocess.run(
                [sys.executable, 'Resources/gui-tool/workshop-tool.py', features_path],
                capture_output=True, text=True
            )
            for line in collab_proc.stdout.splitlines():
                if line.strip().endswith('.json'):
                    features_path = line.strip()
            features_path = os.path.abspath(features_path)
            if not os.path.isfile(features_path):
                self.update_status("Could not determine/copy JSON output file from collaboration tool.")
                return
        except Exception:
            self.update_status("Collaboration tool failed to launch.")
            return

        self.update_status("Submitting data to LLM evaluation engine...")
        result_path = os.path.join(self.session_folder, "llm_eval_output/star_decision_cards.json")
        res = subprocess.run(
            [sys.executable, 'Resources/LLMadapter/openRouter.py', features_path, self.session_folder],
            capture_output=True, text=True
        )

        self.update_status("Awaiting response from AI...")
        # Correct file extraction
        for line in res.stdout.splitlines():
            # Remove 'Ranking result saved to: ' if present
            if line.strip().endswith('.json'):
                if "saved to:" in line:
                    result_path = line.split("saved to:")[-1].strip()
                else:
                    result_path = line.strip()
        result_path = os.path.abspath(result_path)
        logging.info("debug : line159 main")
        self.result_path = result_path

        logging.info("debug : line162 main")
        # Run HTML renderer, save in same folder
        html_path = os.path.join(self.session_folder, "llm_eval_output/star_decision_cards.html")
        res_html = subprocess.run(
            [sys.executable, 'Resources/resultsView/json_to_html.py', result_path, html_path],
            capture_output=True, text=True
        )
        print("STDOUT from json_to_html.py:", res_html.stdout)
        print("STDERR from json_to_html.py:", res_html.stderr)
        for line in res_html.stdout.splitlines():
            if line.strip().endswith('.html'):
                html_path = line.strip()
        html_path = os.path.abspath(html_path)
        self.html_path = html_path
        logging.info("debug : html_path %s", html_path)

        summary_path = os.path.join(self.session_folder, "llm_eval_output/reflexive_summary.html")
        self.summary_path = summary_path

        self.update_status(
            f"LLM evaluation complete!\n\n"
        )
        self.btn_html.config(state=tk.NORMAL)
        self.btn_summary.config(state=tk.NORMAL)
        self.btn_finalize.config(state=tk.NORMAL)
        self.progress.config(text="")

    def update_status(self, message):
        def inner():
            self.msg.config(text=message)
        self.after(0, inner)

    def launch_html(self):
        path = self.html_path
        if not os.path.isfile(path):
            messagebox.showerror("Error", f"HTML file not found:\n{path}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open HTML file:\n{str(e)}")

    def launch_summary(self):
        path = self.summary_path
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open Reflexive Summary file:\n{str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        session_folder = sys.argv[1]
        if not os.path.exists(session_folder):
            os.makedirs(session_folder)
        session_id = os.path.basename(session_folder)
    else:
        randnum = random.randint(1000, 9999)
        dt = datetime.now().strftime("%Y%m%d%H%M%S")
        session_id = f"Session{randnum}_{dt}"
        session_folder = os.path.join("Output", session_id)
        os.makedirs(session_folder, exist_ok=True)
    
    log_filename = os.path.join(session_folder, "debug-prints.log")
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s'
    )

    app = STAR(session_id, session_folder)
    app.mainloop()
