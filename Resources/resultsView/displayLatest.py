import json
import os
import sys
import webbrowser
from glob import glob

# Accept result JSON filename from the command line argument
if len(sys.argv) > 1:
    result_json_filename = sys.argv[1]
else:
    result_files = sorted(glob("Output/ranking_result_*.json"))
    if not result_files:
        raise FileNotFoundError("No results found in Output/ranking_result_*.json!")
    result_json_filename = result_files[-1]

with open(result_json_filename, "r", encoding='utf-8') as f:
    decision_cards = json.load(f)


html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Ranked Feature Decision Cards</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f2f2f2; margin: 0; }
        .container { max-width: 900px; margin: 40px auto; padding: 24px; background: #fff; border-radius: 8px; box-shadow: 0 2px 6px #bbb; }
        .feature { margin-bottom: 32px; padding-bottom: 16px; border-bottom: 1px solid #e0e0e0; }
        .feature:last-child { border-bottom: none; }
        .field { margin: 4px 0; }
        .highlight { font-weight: bold; color: #1976D2; }
        h2 { margin-top: 0; }
    </style>
</head>
<body>
<div class="container">
    <h1>Ranked Feature Decision Cards</h1>
"""

for idx, card in enumerate(decision_cards, 1):
    html += f'''
    <div class="feature">
      <h2>Feature #{idx}: {card.get("summary", "")}</h2>
      <div class="field"><span class="highlight">JIRA Key:</span> {card.get("jira_key", "")}</div>
      <div class="field"><span class="highlight">Priority Score:</span> {card.get("priority_score", "")}</div>
      <div class="field"><span class="highlight">Rationale:</span> {card.get("rationale", "")}</div>
      <div class="field"><span class="highlight">Description:</span> {card.get("description", "")}</div>
      <div class="field"><span class="highlight">Reporter:</span> {card.get("reporter", "")}</div>
      <div class="field"><span class="highlight">Stakeholders:</span> {", ".join(card.get("stakeholders", []))}</div>
      <div class="field"><span class="highlight">Session ID:</span> {card.get("session_id", "")}</div>
      <div class="field"><span class="highlight">Timestamp:</span> {card.get("timestamp", "")}</div>
      <div class="field"><span class="highlight">Module:</span> {card.get("module", "")}</div>
      <div class="field"><span class="highlight">Value Agreement:</span> {card.get("value_agreement", "")}</div>
      <div class="field"><span class="highlight">Dissent:</span> {card.get("dissent", "")}</div>
      <div class="field"><span class="highlight">Dependencies:</span> {card.get("dependencies", "")}</div>
      <div class="field"><span class="highlight">Biases:</span> {card.get("biases", "")}</div>
      <div class="field"><span class="highlight">Synthesis Summary:</span> {card.get("synthesis_summary", "")}</div>
    </div>
    '''

html += """
</div>
</body>
</html>
"""

output_html = "Output/ranked_features.html"
with open(output_html, "w", encoding="utf-8") as f:
    f.write(html)

webbrowser.open('file://' + os.path.realpath(output_html))
print(f"HTML report generated: {output_html}")
