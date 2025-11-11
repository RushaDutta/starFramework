import sys
import os
import json
import webbrowser
import logging
import traceback

def main():
    print("displayLatest.py called with args:", sys.argv)
    # Parse arguments and set up paths
    if len(sys.argv) > 2:
        result_json_filename = sys.argv[1]
        output_html = sys.argv[2]
        session_folder = os.path.dirname(result_json_filename)
    elif len(sys.argv) > 1:
        result_json_filename = sys.argv[1]
        session_folder = os.path.dirname(result_json_filename)
        output_html = os.path.join(session_folder, "llm_eval_output/star_decision_cards.html")
    else:
        print("ERROR: Usage: python displayLatest.py <result_json_filename> <output_html_filename>")
        sys.exit(1)

    # Set up logging
    log_filename = os.path.join(session_folder, "debug-prints.log")
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s'
    )

    logging.info("displayLatest.py args: %s", sys.argv)
    logging.info("result_json_filename: %s", result_json_filename)
    logging.info("output_html: %s", output_html)

    try:
        # Ensure output folder exists
        html_dir = os.path.dirname(output_html)
        print(f"Ensuring output folder exists: {html_dir}")
        logging.info("Ensuring output folder exists: %s", html_dir)
        os.makedirs(html_dir, exist_ok=True)

        # Check if input JSON file exists
        if not os.path.isfile(result_json_filename):
            msg = f"Input JSON file not found: {result_json_filename}"
            print("ERROR:", msg)
            logging.error(msg)
            sys.exit(2)

        with open(result_json_filename, "r", encoding="utf-8") as f:
            decision_cards = json.load(f)

        if isinstance(decision_cards, list):
            logging.info("Loaded decision cards count: %s", len(decision_cards))
        else:
            logging.info("Loaded decision_cards type: %s", type(decision_cards))

        # List fields, REMOVED issue_key (and aliases) everywhere, KEEP ONLY jira_id as main unique key for display
        all_fields = [
            "issue_type",
            "jira_key", "jira_id",  # Will both resolve to the same value; use jira_id as preferred key
            "summary",
            "reporter", "reporter_id",
            "status",
            "custom_field_evidencelink",
            "description",
            "labels",
            "custom_field_stakeholders", "stakeholders",
            "custom_field_module", "module",
            "session_id", "facilitator_id", "timestamp",
            "value_agreement", "dissent", "dependencies", "biases",
            "priority_score", "rationale"
        ]

        llm_output_fields = {"priority_score", "rationale"}

        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Ranked Feature Decision Cards</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f2f2f2; margin: 0; }
                .container { max-width: 950px; margin: 40px auto; padding: 24px; background: #fff; border-radius: 8px; box-shadow: 0 2px 6px #bbb; }
                .feature { margin-bottom: 32px; padding-bottom: 16px; border-bottom: 1px solid #e0e0e0; }
                .feature:last-child { border-bottom: none; }
                .field { margin: 4px 0; }
                .highlight { font-weight: bold; color: #1976D2; }
                .llmfield { font-weight: bold; color: #c2185b; }
                h2 { margin-top: 0; }
            </style>
        </head>
        <body>
        <div class="container">
            <h1>Ranked Feature Decision Cards</h1>
        """
        for idx, card in enumerate(decision_cards, 1):
            html += f'<div class="feature">\n'
            html += f'<h2>Feature #{idx}: {card.get("summary", "")}</h2>\n'

            for key in all_fields:
                # REMOVE issue_key/alias to NOT render at all (just ignore key "issue_key")
                if key == "issue_key":
                    continue
                display_name = key.replace("_", " ").title()
                variants = [key]
                if key == "jira_key":
                    variants += ["jira_id"]
                if key == "custom_field_stakeholders":
                    variants += ["stakeholders"]
                if key == "custom_field_module":
                    variants += ["module"]
                value = ""
                for v in variants:
                    if v in card:
                        value = card[v]
                        break
                if value == "" and key not in llm_output_fields:
                    continue
                if isinstance(value, (list, tuple)):
                    value = ", ".join(str(x) for x in value)
                extra_class = "llmfield" if key in llm_output_fields else "highlight"
                html += f'<div class="field"><span class="{extra_class}">{display_name}:</span> {value}</div>\n'
            html += '</div>\n'

        html += """
        </div>
        </body>
        </html>
        """

        print(f"Writing HTML to {output_html}")
        logging.info("Writing HTML to %s", output_html)
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html)

        print(output_html)
        logging.info("Successfully wrote HTML file: %s", output_html)

        try:
            webbrowser.open('file://' + os.path.realpath(output_html))
        except Exception as e:
            print(f"Failed to open HTML in browser: {str(e)}")
            logging.error(f"Failed to open HTML in browser: {str(e)}")

    except Exception as exc:
        msg = f"Exception in displayLatest.py: {str(exc)}"
        print(msg)
        traceback.print_exc()
        logging.error(msg)
        sys.exit(3)

if __name__ == "__main__":
    main()
