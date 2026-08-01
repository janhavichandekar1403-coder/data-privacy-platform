"""
app.py
------
Main Flask server for the AI Privacy-Preserving Data
Anonymization Platform (MVP version).

Routes:
  GET  /                 -> serves the frontend page
  POST /upload            -> upload a CSV, run PII detection
  POST /process            -> apply chosen anonymization methods
  GET  /download/<name>   -> download the anonymized CSV or PDF report
"""

import os
import uuid
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_from_directory

from detector import detect_pii_columns, calculate_privacy_risk_score
from anonymizer import apply_method, generate_encryption_key, Tokenizer
from report_generator import generate_compliance_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)

# Very simple in-memory "session store" so multiple uploads don't clash.
# Key = session_id, Value = { "path": ..., "df": ..., "filename": ... }
SESSIONS = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported in this version"}), 400

    session_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_DIR, f"{session_id}.csv")
    file.save(saved_path)

    df = pd.read_csv(saved_path)
    detected_columns = detect_pii_columns(df)
    risk_before = calculate_privacy_risk_score(detected_columns)

    SESSIONS[session_id] = {
        "path": saved_path,
        "filename": file.filename,
        "risk_before": risk_before,
    }

    return jsonify({
        "session_id": session_id,
        "filename": file.filename,
        "num_records": len(df),
        "columns": detected_columns,
        "risk_before": risk_before,
    })


@app.route("/process", methods=["POST"])
def process():
    data = request.get_json()
    session_id = data.get("session_id")
    column_methods = data.get("column_methods")  # { "email": "mask", "name": "tokenize", ... }

    if session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session. Please upload the file again."}), 400

    session = SESSIONS[session_id]
    df = pd.read_csv(session["path"])

    key = generate_encryption_key()
    tokenizer = Tokenizer()
    column_actions = []
    encryption_used = False
    tokenization_used = False

    for column, method in column_methods.items():
        if column not in df.columns or method == "skip":
            continue
        if method == "encrypt":
            encryption_used = True
        if method == "tokenize":
            tokenization_used = True
        df[column] = df[column].apply(
            lambda v: apply_method(v, method, key=key, tokenizer=tokenizer)
        )
        column_actions.append({"column": column, "label": method, "method": method})

    # Save anonymized dataset
    output_csv_name = f"{session_id}_anonymized.csv"
    output_csv_path = os.path.join(OUTPUT_DIR, output_csv_name)
    df.to_csv(output_csv_path, index=False)

    # Re-run detection on the anonymized data for an "after" risk score
    detected_after = detect_pii_columns(df)
    risk_after = calculate_privacy_risk_score(detected_after)

    # Build the compliance report
    report_name = f"{session_id}_report.pdf"
    report_path = os.path.join(OUTPUT_DIR, report_name)
    generate_compliance_report(
        dataset_name=session["filename"],
        num_records=len(df),
        column_actions=column_methods_to_labels(column_methods),
        risk_before=session["risk_before"],
        risk_after=risk_after,
        output_path=report_path,
    )

    return jsonify({
        "risk_before": session["risk_before"],
        "risk_after": risk_after,
        "csv_download": output_csv_name,
        "report_download": report_name,
        # Only sent back if at least one column actually used that method
        "encryption_key": key.decode("utf-8") if encryption_used else None,
        "token_mapping": tokenizer.mapping_table if tokenization_used else [],
    })


def column_methods_to_labels(column_methods):
    return [{"column": c, "label": m, "method": m} for c, m in column_methods.items()]


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
