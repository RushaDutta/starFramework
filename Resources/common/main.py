import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox
import sys
import os

class STAROrchestrator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("STARFramework Orchestrator")
        self.geometry("470x230")
        self.resizable(False, False)
        
        self.msg = tk.Label(self, text="Ready.\nClick Finalize to begin feature ranking...", pady=12)
        self.msg.pack()
        
        self.btn_finalize = tk.Button(self, text="Launch STAR GUI tool", command=self.finalize, padx=20, pady=6)
        self.btn_finalize.pack(pady=8)
        
        self.btn_html = tk.Button(self, text="View Latest HTML Results", command=self.launch_html, padx=20, pady=6, state=tk.DISABLED)
        self.btn_html.pack(pady=8)
        
        self.progress = tk.Label(self, text="", fg="#999", font=("Arial", 11))
        self.progress.pack()
        
        self.result_path = ""   # <- Hold result filename

    def finalize(self):
        self.msg.config(text="Launching collaboration tool for input...\n")
        self.progress.config(text="")
        self.btn_finalize.config(state=tk.DISABLED)
        self.btn_html.config(state=tk.DISABLED)   # Disable BOTH buttons
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
        # Run collaboration tool, capture output
        try:
            collab_proc = subprocess.run(
                [sys.executable, 'Resources/gui-tool/collaboration-tool.py'],
                capture_output=True, text=True
            )
            features_path = None
            # Find the printed path (should end in .json)
            for line in collab_proc.stdout.splitlines():
                if line.strip().endswith('.json'):
                    features_path = line.strip()
            if not features_path:
                self.update_status("Could not determine JSON output file from collaboration tool.")
                return  # Don't proceed!
        except Exception:
            self.update_status("Collaboration tool failed to launch.")
            return


        self.update_status("Submitting data to LLM evaluation engine...")
        res = subprocess.run(
            [sys.executable, 'Resources/LLMadapter/openRouter.py', features_path],
            capture_output=True, text=True
        )

        self.update_status("Awaiting response from AI...")

        # Parse result file location from stdout; this is critical for next step
        result_path = ""
        for line in res.stdout.splitlines():
            if "Ranking result saved to" in line:
                result_path = line.split(":")[1].strip()
        if not result_path:
            result_path = "Output/ranking_result_latest.json"
        
        self.result_path = result_path  # store for button + viewer

        # Generate HTML using the result_path as input
        try:
            subprocess.run([sys.executable, 'Resources/resultsView/displayLatest.py', result_path])
            self.update_status(f"Ranking results saved to:\n{result_path}\nReady to view results.")
            self.btn_html.config(state=tk.NORMAL)
        except Exception as e:
            self.update_status(f"Ranking results saved to:\n{result_path}\n(ERROR opening HTML: {str(e)})")
            self.btn_html.config(state=tk.NORMAL)
        
        self.btn_finalize.config(state=tk.NORMAL)
        self.progress.config(text="")

    def update_status(self, message):
        def inner():
            self.msg.config(text=message)
        self.after(0, inner)

    def launch_html(self):
        # Pass the exact result path to displayLatest.py for HTML rendering
        try:
            subprocess.Popen([sys.executable, 'Resources/resultsView/displayLatest.py', self.result_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch HTML viewer:\n{str(e)}")

if __name__ == "__main__":
    app = STAROrchestrator()
    app.mainloop()
