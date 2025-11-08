import csv
import json
import os
import re
from datetime import datetime
import tkinter as tk
import tkinter.font
from tkinter import ttk, messagebox, filedialog, simpledialog
import sys

def load_all_json(json_path):
    if not os.path.exists(json_path):
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_all_json(json_path, data):
    output_dir = os.path.dirname(json_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def validate_json_schema(data):
    required = [
        "jira_key", "summary", "description", "reporter", "stakeholders", "evidence", "module",
        "value_agreement", "dissent", "dependencies", "biases", "synthesis_summary",
        "session_id", "facilitator_id", "timestamp"
    ]
    for idx, record in enumerate(data):
        for k in required:
            if k not in record:
                raise ValueError(f"Missing '{k}' in record at index {idx}")
    return True

def is_valid_email(addr):
    return bool(re.match(r"^[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+$", addr))

class EmailPrompt(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Facilitator Login")
        self.geometry("420x140")
        self.resizable(False, False)
        self.grab_set()
        email_font = tkinter.font.Font(family="Arial", size=16)
        instr = tk.Label(self, text="Enter Facilitator email ID :", font=("Arial", 14, "bold"))
        instr.pack(pady=12)
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.entry_var, font=email_font, width=30)
        self.entry.pack(pady=7)
        self.entry.focus_set()
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=8)
        submit_btn = tk.Button(btn_frame, text="Submit", font=("Arial", 13), command=self.on_submit, width=10, bg="#1976d2", fg="white")
        submit_btn.pack(side="left", padx=10)
        cancel_btn = tk.Button(btn_frame, text="Cancel", font=("Arial", 13), command=self.on_cancel, width=10)
        cancel_btn.pack(side="left", padx=10)
        self.result = None

    def on_submit(self):
        self.result = self.entry_var.get()
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

class StoryApp:
    def __init__(self, root, facilitator_id, session_folder):
        self.root = root
        self.root.title("STAR Workshop Tool")
        self.root.configure(bg="#e3eafc")

        # Accept session folder/external session id (do NOT generate yourself unless debug/manual run!)
        self.session_folder = session_folder
        self.session_id = os.path.basename(session_folder)
        self.data_json_path = os.path.join(self.session_folder, "consolidated_reasoning.json")

        self.facilitator_id = facilitator_id
        self.csv_data = []
        self.story_by_key = {}
        self.entry_fields = {}
        self.loaded_json = load_all_json(self.data_json_path)
        self.setup_styles()
        self.build_layout()
        self.load_csv_dialog()
        self.disable_all_except_jira_key()

    def setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('Section.TLabelframe.Label', foreground='#fff', background='#1976d2', font=('Arial', 13, 'bold'))
        style.configure('Section.TLabelframe', background='#e3eafc', borderwidth=2, relief="ridge")
        style.configure('TLabel', font=('Arial', 12))
        style.configure('TButton', font=('Arial', 12, 'bold'), background="#1976d2", foreground='white')
        style.configure('Em.TButton', font=('Arial', 11, 'bold'), background="#c2185b", foreground='#fff')
        style.configure('TEntry', font=('Arial', 12))
        style.configure('TCombobox', font=('Arial', 12))
        style.map('TButton', background=[('active', '#42a5f5')])

    def build_layout(self):
        pad_x = 16
        pad_y = 10
        loader = ttk.Frame(self.root)
        loader.pack(fill="x", padx=pad_x, pady=pad_y)
        # Session label at top right
        self.session_label = ttk.Label(
            loader,
            text=f"Session: {self.session_id}",
            foreground="#1976d2",
            font=("Arial", 10, "italic")
        )
        self.session_label.pack(side="right", padx=8)
        ttk.Label(loader, text="CSV File:").pack(side="left")
        self.csv_path_var = tk.StringVar()
        csv_entry = ttk.Entry(loader, textvariable=self.csv_path_var, width=55)
        csv_entry.pack(side="left")
        btn_load = ttk.Button(loader, text="Browse & Load", command=self.load_csv_dialog)
        btn_load.pack(side="left", padx=10)

        issue_frame = ttk.LabelFrame(self.root, text="1. Select Jira Issue", style="Section.TLabelframe", labelanchor="nw", padding=(pad_x, pad_y))
        issue_frame.pack(fill="x", padx=pad_x, pady=pad_y)
        ttk.Label(issue_frame, text="Jira Issue Key:").grid(row=0, column=0, sticky="w")
        self.jira_key_var = tk.StringVar()
        self.jira_key_combo = ttk.Combobox(issue_frame, textvariable=self.jira_key_var, state="readonly", width=40)
        self.jira_key_combo.grid(row=0, column=1, sticky="w", padx=8)
        self.jira_key_combo.bind("<<ComboboxSelected>>", self.on_story_selected)

        autofill_frame = ttk.LabelFrame(self.root, text="2. Story Details", style="Section.TLabelframe", labelanchor="nw", padding=(pad_x, pad_y))
        autofill_frame.pack(fill="x", padx=pad_x, pady=pad_y)
        self.detail_vars = {}
        for idx, field in enumerate(["summary", "description", "reporter", "stakeholders", "evidence", "module"]):
            label = ttk.Label(autofill_frame, text=f"{field.title()}:")
            label.grid(row=idx, column=0, sticky="w")
            if field == "description":
                desc_widget = tk.Text(autofill_frame, height=3, width=52, bg="#f1f8e9", wrap="word", font=('Arial', 12))
                desc_widget.grid(row=idx, column=1, sticky="w", padx=6)
                self.detail_vars[field] = desc_widget
            else:
                entry = ttk.Entry(autofill_frame, state="readonly", width=54)
                entry.grid(row=idx, column=1, sticky="w", padx=6)
                self.detail_vars[field] = entry

        entry_frame = ttk.LabelFrame(self.root, text="3. Facilitation Outcome", style="Section.TLabelframe", labelanchor="nw", padding=(pad_x, pad_y))
        entry_frame.pack(fill="x", padx=pad_x, pady=pad_y)
        fields = [("value_agreement", "Value Agreement"),
                  ("dissent", "Dissenting Opinion"),
                  ("dependencies", "Dependencies"),
                  ("biases", "Biases Observed"),
                  ("synthesis_summary", "Synthesis Summary")]
        for idx, (field, label) in enumerate(fields):
            l = ttk.Label(entry_frame, text=f"{label}:")
            l.grid(row=idx, column=0, sticky="w")
            var = tk.StringVar()
            entry = ttk.Entry(entry_frame, textvariable=var, width=54)
            entry.grid(row=idx, column=1, sticky="w", padx=6)
            self.entry_fields[field] = (var, entry)

        btn_frame = tk.Frame(self.root, bg="#e3eafc")
        btn_frame.pack(fill="x", pady=(12, 18))
        self.submit_btn = tk.Button(btn_frame, text="Submit Story", font=('Arial', 12, 'bold'), bg="#43a047", fg="#fff",
                                    activebackground="#388e3c", padx=18, pady=8, relief="ridge",
                                    command=self.submit_story)
        self.submit_btn.pack(side="right", padx=16)
        self.finalize_btn = tk.Button(btn_frame, text="Finalize & End Session", font=('Arial', 12, 'bold'), bg="#F7FA8E", fg="#332EAB",
                                      activebackground="#D6D37A", padx=18, pady=8, relief="ridge",
                                      command=self.finalize_and_quit)
        self.finalize_btn.pack(side="right", padx=16)

    def load_csv_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        self.csv_path_var.set(path)
        self.load_csv(path)

    def load_csv(self, path):
        try:
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.csv_data = [row for row in reader]
            self.story_by_key = {row["Issue key"]: row for row in self.csv_data if "Issue key" in row}
            keys = sorted(self.story_by_key.keys())
            self.jira_key_combo['values'] = keys
            self.jira_key_var.set("")
            self.reset_details_and_inputs()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV:\n{e}")

    def on_story_selected(self, event=None):
        key = self.jira_key_var.get()
        row = self.story_by_key.get(key)
        if not row:
            self.reset_details_and_inputs()
            self.disable_all_except_jira_key()
            return
        for field in ["summary", "description", "reporter", "stakeholders", "evidence", "module"]:
            value = row.get(field.title(), "") or row.get(field, "")
            if field == "description":
                self.detail_vars[field].configure(state="normal")
                self.detail_vars[field].delete("1.0", "end")
                self.detail_vars[field].insert("1.0", value)
                self.detail_vars[field].configure(state="disabled")
            else:
                self.detail_vars[field].configure(state="normal")
                self.detail_vars[field].delete(0, "end")
                self.detail_vars[field].insert(0, value)
                self.detail_vars[field].configure(state="readonly")
        self.enable_entry_fields()

    def disable_all_except_jira_key(self):
        for var, entry in self.entry_fields.values():
            entry.configure(state="disabled")

    def enable_entry_fields(self):
        for var, entry in self.entry_fields.values():
            entry.configure(state="normal")

    def reset_details_and_inputs(self):
        for v in self.detail_vars.values():
            if isinstance(v, tk.Text):
                v.configure(state="normal")
                v.delete("1.0", "end")
                v.configure(state="disabled")
            else:
                v.configure(state="normal")
                v.delete(0, "end")
                v.configure(state="readonly")
        for var, entry in self.entry_fields.values():
            var.set("")
        self.disable_all_except_jira_key()

    def submit_story(self):
        key = self.jira_key_var.get()
        if not key:
            messagebox.showwarning("Missing", "Please select a Jira Issue Key.")
            return
        existing = [r for r in self.loaded_json if r.get("jira_key") == key and r.get("session_id") == self.session_id]
        if existing:
            messagebox.showerror("Duplicate", f"Jira Issue {key} has already been entered in this session.")
            return
        row = self.story_by_key.get(key, {})
        record = {
            "jira_key": key,
            "summary": row.get("Summary", "") or row.get("summary", ""),
            "description": row.get("Description", "") or row.get("description", ""),
            "reporter": row.get("Reporter", "") or row.get("reporter", ""),
            "stakeholders": row.get("Stakeholders", "") or row.get("stakeholders", ""),
            "evidence": row.get("Evidence", "") or row.get("evidence", ""),
            "module": row.get("Module", "") or row.get("module", ""),
            "session_id": self.session_id,
            "facilitator_id": self.facilitator_id,
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z"
        }
        for k in ["value_agreement", "dissent", "dependencies", "biases", "synthesis_summary"]:
            record[k] = self.entry_fields[k][0].get()
        self.loaded_json.append(record)
        save_all_json(self.data_json_path, self.loaded_json)
        messagebox.showinfo("Saved", f"Data for Jira Issue {key} has been saved.")

        keys_left = [v for v in self.jira_key_combo['values'] if v != key]
        self.jira_key_combo['values'] = keys_left
        self.jira_key_var.set("")
        self.reset_details_and_inputs()
        if not keys_left:
            self.submit_btn.configure(state="disabled")

    def finalize_and_quit(self):
        try:
            validate_json_schema(self.loaded_json)
            print(self.data_json_path)
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Validation Error", f"Could not finalize session:\n{e}")

def main():
    # Accept session folder from command line (or generate if manual/debug run)
    if len(sys.argv) > 1:
        session_folder = sys.argv[1]
        if not os.path.exists(session_folder):
            os.makedirs(session_folder)
        session_id = os.path.basename(session_folder)
    else:
        # fallback for debug/manual usage
        import random
        randnum = random.randint(1000, 9999)
        dt = datetime.now().strftime("%Y%m%d%H%M%S")
        session_id = f"Session{randnum}_{dt}"
        session_folder = os.path.join("Output", session_id)
        os.makedirs(session_folder, exist_ok=True)
    root = tk.Tk()
    root.withdraw()
    facilitator_id = None
    while True:
        dlg = EmailPrompt(root)
        root.wait_window(dlg)
        facilitator_id = dlg.result
        if facilitator_id is None:
            messagebox.showerror("No Facilitator ID", "Facilitator email is required to start the session.")
            root.destroy()
            return
        if is_valid_email(facilitator_id):
            break
        else:
            messagebox.showerror("Invalid Email", "Please enter a valid email address as Facilitator ID.")
    root.deiconify()
    app = StoryApp(root, facilitator_id, session_folder)
    root.mainloop()

if __name__ == "__main__":
    main()
