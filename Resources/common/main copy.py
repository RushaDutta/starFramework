import subprocess
import os
import sys
import tkinter as tk
from tkinter import messagebox

def run_collaboration_tool():
    subprocess.run([sys.executable, 'Resources/gui-tool/collaboration-tool.py'])

def run_openrouter(features_path):
    # Make sure you pass the path if needed; update openRouter.py to accept it as an argument
    p = subprocess.run([sys.executable, 'Resources/LLMadapter/openRouter.py', features_path], capture_output=True, text=True)
    print(p.stdout)
    # Parse for "Ranking results saved to:" or just grab the output path
    for line in p.stdout.splitlines():
        if "Ranking result saved to" in line:
            result_path = line.split(":")[1].strip()
            return result_path
    # Fallback if not found
    return "Output/latest_file.json"

def launch_html():
    subprocess.Popen([sys.executable, '../resultsView/displayLatest.py'])

def main_flow():
    run_collaboration_tool()
    features_path = 'Resources/LLMadapter/features.json'  # Or let user choose
    
    result_path = run_openrouter(features_path)
    print(f"Ranking results saved to: {result_path}")
    
    # Display a GUI button to view results
    root = tk.Tk()
    root.title("STARFramework Orchestrator")
    msg = tk.Label(root, text=f"Ranking results saved to:\n{result_path}", pady=10)
    msg.pack()
    btn = tk.Button(root, text="View HTML Results", command=launch_html, padx=30, pady=10)
    btn.pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    main_flow()
