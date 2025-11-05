import csv
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from git import Repo

# Git repo info
GIT_REPO_URL = "https://github.com/RushaDutta/starFramework.git"  # Change this to your repo URL
LOCAL_REPO_DIR = "C:/temp_repo/"  # Local folder path for cloning
CSV_PATH_IN_REPO = "Test/testdata/dummy_user_stories.csv"  # Relative CSV path inside repo
XML_PATH_IN_REPO = "Output/stories.xml"  # Relative XML output path inside repo

# Clone or update the git repository to ensure latest
def clone_or_update_repo():
    if not os.path.exists(LOCAL_REPO_DIR):
        print("Cloning repo...")
        Repo.clone_from(GIT_REPO_URL, LOCAL_REPO_DIR)
    else:
        print("Fetching latest changes...")
        repo = Repo(LOCAL_REPO_DIR)
        origin = repo.remotes.origin
        origin.pull()

# Set file paths to be inside the local clone of Git repo
DEFAULT_CSV_PATH = os.path.join(LOCAL_REPO_DIR, CSV_PATH_IN_REPO)
XML_OUTPUT_PATH = os.path.join(LOCAL_REPO_DIR, XML_PATH_IN_REPO)

# XML helpers
def ensure_xml_root(xml_path):
    if not os.path.exists(xml_path) or os.path.getsize(xml_path) == 0:
        root = ET.Element("Stories")
        tree = ET.ElementTree(root)
        os.makedirs(os.path.dirname(xml_path), exist_ok=True)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    tree = ET.parse(xml_path)
    return tree

def story_exists(xml_tree, user_story_id):
    root = xml_tree.getroot()
    for story in root.findall("Story"):
        sid = story.findtext("UserStoryID")
        if sid == user_story_id:
            return True
    return False

def append_story(xml_tree, story_payload):
    root = xml_tree.getroot()
    story_el = ET.SubElement(root, "Story")
    # Required base fields
    for key in [
        "UserStoryID", "JiraID", "Title", "Description",
        "Author", "Stakeholders"
    ]:
        el = ET.SubElement(story_el, key)
        el.text = story_payload.get(key, "") or ""

    # PM/Team input fields
    inputs_el = ET.SubElement(story_el, "Inputs")
    for key in [
        "PM_Comments", "Developer_Comments", "QA_Comments", "Risk",
        "Dependencies", "Priority", "Rationale", "TradeOffs", "Outcome",
        "Status", "ReviewedBy", "DiscussionDate", "FinalDecision"
    ]:
        el = ET.SubElement(inputs_el, key)
        el.text = story_payload.get(key, "") or ""

    # Meta
    meta_el = ET.SubElement(story_el, "Meta")
    ts_el = ET.SubElement(meta_el, "SubmittedAt")
    ts_el.text = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    xml_tree.write(XML_OUTPUT_PATH, encoding="utf-8", xml_declaration=True)

def commit_changes(user_story_id):
    repo = Repo(LOCAL_REPO_DIR)
    repo.git.add(XML_PATH_IN_REPO)
    commit_msg = f"Add details for UserStoryID {user_story_id}"
    repo.index.commit(commit_msg)
    origin = repo.remotes.origin
    origin.push()
    print(f"Committed and pushed changes for {user_story_id}")

# Tkinter App
class StoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("User Story Entry to XML")

        self.csv_data = []
        self.headers = []
        self.story_by_id = {}

        self.build_layout()
        self.load_csv(DEFAULT_CSV_PATH)
        self.configure_initial_state()

    def build_layout(self):
        pad = {"padx": 8, "pady": 6}

        # Top: CSV filepath display and reload
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", **pad)

        ttk.Label(top_frame, text="CSV File:").pack(side="left")
        self.csv_path_var = tk.StringVar(value=DEFAULT_CSV_PATH)
        self.csv_entry = ttk.Entry(top_frame, textvariable=self.csv_path_var, width=60)
        self.csv_entry.pack(side="left", padx=6)
        ttk.Button(top_frame, text="Browse", command=self.browse_csv).pack(side="left")
        ttk.Button(top_frame, text="Reload", command=self.reload_csv).pack(side="left", padx=4)

        # UserStoryID selector
        sel_frame = ttk.LabelFrame(self.root, text="Select User Story")
        sel_frame.pack(fill="x", **pad)

        ttk.Label(sel_frame, text="UserStoryID:").grid(row=0, column=0, sticky="w", **pad)
        self.user_story_var = tk.StringVar()
        self.user_story_combo = ttk.Combobox(sel_frame, textvariable=self.user_story_var, state="readonly", width=30)
        self.user_story_combo.grid(row=0, column=1, sticky="w", **pad)
        self.user_story_combo.bind("<<ComboboxSelected>>", self.on_story_selected)

        # Auto-populated fields (readonly)
        auto_frame = ttk.LabelFrame(self.root, text="Auto-populated from CSV")
        auto_frame.pack(fill="x", **pad)

        self.jira_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.author_var = tk.StringVar()
        self.stakeholders_var = tk.StringVar()

        ttk.Label(auto_frame, text="JiraID:").grid(row=0, column=0, sticky="w", **pad)
        self.jira_entry = ttk.Entry(auto_frame, textvariable=self.jira_var, state="readonly", width=40)
        self.jira_entry.grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(auto_frame, text="Title:").grid(row=1, column=0, sticky="w", **pad)
        self.title_entry = ttk.Entry(auto_frame, textvariable=self.title_var, state="readonly", width=80)
        self.title_entry.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(auto_frame, text="Author:").grid(row=2, column=0, sticky="w", **pad)
        self.author_entry = ttk.Entry(auto_frame, textvariable=self.author_var, state="readonly", width=40)
        self.author_entry.grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(auto_frame, text="Stakeholders:").grid(row=3, column=0, sticky="w", **pad)
        self.stakeholders_entry = ttk.Entry(auto_frame, textvariable=self.stakeholders_var, state="readonly", width=80)
        self.stakeholders_entry.grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(auto_frame, text="Description:").grid(row=4, column=0, sticky="nw", **pad)
        self.description_text = tk.Text(auto_frame, height=5, width=80, wrap="word")
        self.description_text.grid(row=4, column=1, sticky="we", **pad)
        self.description_text.configure(state="disabled")

        # Input fields
        inputs_frame = ttk.LabelFrame(self.root, text="PM & Team Inputs")
        inputs_frame.pack(fill="x", **pad)

        self.inputs = {}
        single_line_fields = [
            "PM_Comments", "Developer_Comments", "QA_Comments", "Risk",
            "Dependencies", "Priority", "Rationale", "TradeOffs",
            "Outcome", "Status", "ReviewedBy", "DiscussionDate", "FinalDecision"
        ]

        row = 0
        for field in single_line_fields:
            ttk.Label(inputs_frame, text=f"{field}:").grid(row=row, column=0, sticky="w", **pad)
            var = tk.StringVar()
            entry = ttk.Entry(inputs_frame, textvariable=var, width=80)
            entry.grid(row=row, column=1, sticky="w", **pad)
            self.inputs[field] = (var, entry)
            row += 1

        # Action buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", **pad)
        self.submit_btn = ttk.Button(btn_frame, text="Submit", command=self.submit)
        self.submit_btn.pack(side="right", padx=4)
        ttk.Button(btn_frame, text="Quit", command=self.root.quit).pack(side="right", padx=4)

    def configure_initial_state(self):
        # Only UserStoryID active, others disabled
        self.set_inputs_state("disabled")
        self.set_autofill_state(readonly=True)

    def set_autofill_state(self, readonly=True):
        state = "readonly" if readonly else "normal"
        self.jira_entry.configure(state=state)
        self.title_entry.configure(state=state)
        self.author_entry.configure(state=state)
        self.stakeholders_entry.configure(state=state)
        self.description_text.configure(state="disabled" if readonly else "normal")

    def set_inputs_state(self, state):
        for _, entry in self.inputs.values():
            entry.configure(state=state)
        self.submit_btn.configure(state=state)

    def browse_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.csv_path_var.set(path)
            self.load_csv(path)

    def reload_csv(self):
        self.load_csv(self.csv_path_var.get())

    def load_csv(self, path):
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.headers = reader.fieldnames
                self.csv_data = [row for row in reader]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV:\n{e}")
            return

        self.story_by_id = {}
        for row in self.csv_data:
            sid = row.get("UserStoryID", "").strip()
            if sid:
                self.story_by_id[sid] = row

        ids = sorted(self.story_by_id.keys())
        self.user_story_combo["values"] = ids
        self.user_story_var.set("")
        self.clear_autofill()
        self.clear_inputs()
        self.configure_initial_state()

    def clear_autofill(self):
        self.jira_var.set("")
        self.title_var.set("")
        self.author_var.set("")
        self.stakeholders_var.set("")
        self.description_text.configure(state="normal")
        self.description_text.delete("1.0", "end")
        self.description_text.configure(state="disabled")

    def clear_inputs(self):
        for var, _ in self.inputs.values():
            var.set("")

    def on_story_selected(self, event=None):
        sid = self.user_story_var.get()
        row = self.story_by_id.get(sid)
        if not row:
            self.clear_autofill()
            self.set_inputs_state("disabled")
            return

        self.jira_var.set(row.get("JiraID", ""))
        self.title_var.set(row.get("Title", ""))
        self.author_var.set(row.get("Author", ""))
        self.stakeholders_var.set(row.get("Stakeholders", ""))
        self.description_text.configure(state="normal")
        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", row.get("Description", ""))
        self.description_text.configure(state="disabled")

        self.set_inputs_state("normal")

    def gather_payload(self):
        sid = self.user_story_var.get().strip()
        if not sid:
            messagebox.showwarning("Missing", "Please select a UserStoryID.")
            return None

        row = self.story_by_id.get(sid, {})
        payload = {
            "UserStoryID": sid,
            "JiraID": row.get("JiraID", ""),
            "Title": row.get("Title", ""),
            "Description": row.get("Description", ""),
            "Author": row.get("Author", ""),
            "Stakeholders": row.get("Stakeholders", "")
        }

        for key, (var, _) in self.inputs.items():
            payload[key] = var.get().strip()

        dd = payload.get("DiscussionDate", "")
        if dd:
            try:
                _ = datetime.fromisoformat(dd.replace("Z", "+00:00")) if ("T" in dd or "-" in dd) else datetime.strptime(dd, "%Y-%m-%d")
            except Exception:
                if not messagebox.askyesno("Date format", "DiscussionDate doesn't look ISO 8601. Continue anyway?"):
                    return None

        return payload

    def submit(self):
        payload = self.gather_payload()
        if not payload:
            return

        tree = ensure_xml_root(XML_OUTPUT_PATH)
        if story_exists(tree, payload["UserStoryID"]):
            messagebox.showerror("Duplicate", f"UserStoryID {payload['UserStoryID']} already exists in {XML_OUTPUT_PATH}.")
            return

        append_story(tree, payload)
        commit_changes(payload["UserStoryID"])
        messagebox.showinfo("Saved", f"Story {payload['UserStoryID']} appended to {XML_OUTPUT_PATH}.")
        self.set_inputs_state("disabled")

def main():
    clone_or_update_repo()
    root = tk.Tk()
    app = StoryApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
