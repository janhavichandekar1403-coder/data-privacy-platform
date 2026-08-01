"""
detector.py
-----------
Detects which columns in a dataset likely contain
Personally Identifiable Information (PII).

Two detection strategies are combined:
1. Rule-based: checks the COLUMN NAME against a list of known
   sensitive keywords (e.g. "email", "phone", "aadhaar").
2. Regex-based: checks a SAMPLE OF VALUES in the column against
   regex patterns for emails, phone numbers, Aadhaar, PAN, etc.

Each column gets a confidence score from 0-100 and a list of
reasons explaining why it was flagged.
"""

import re

# ---- 1. Keywords that suggest a column name is sensitive ----
SENSITIVE_KEYWORDS = {
    "name": "Name",
    "full_name": "Name",
    "fname": "Name",
    "lname": "Name",
    "email": "Email",
    "mail": "Email",
    "phone": "Phone Number",
    "mobile": "Phone Number",
    "contact": "Phone Number",
    "address": "Address",
    "aadhaar": "Aadhaar Number",
    "aadhar": "Aadhaar Number",
    "pan": "PAN Number",
    "ssn": "Social Security Number",
    "passport": "Passport Number",
    "dob": "Date of Birth",
    "birth": "Date of Birth",
    "account": "Account Number",
    "card": "Card Number",
    "credit": "Card Number",
    "gender": "Gender",
    "salary": "Salary / Financial Info",
}

# ---- 2. Regex patterns that suggest VALUES are sensitive ----
REGEX_PATTERNS = {
    "Email": re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$"),
    "Phone Number": re.compile(r"^\+\d{1,3}\d{10}$|^\d{10}$"),
    "Aadhaar Number": re.compile(r"^\d{4}\s?\d{4}\s?\d{4}$"),
    "PAN Number": re.compile(r"^[A-Z]{5}\d{4}[A-Z]$"),
}


def _keyword_match(column_name: str):
    """Check if the column name itself hints at sensitive data."""
    col = column_name.strip().lower().replace(" ", "_")
    for keyword, label in SENSITIVE_KEYWORDS.items():
        if keyword in col:
            return label
    return None


def _regex_match_ratio(series):
    """
    Try every regex pattern against a sample of values in the column.
    Returns (best_label, match_ratio) - the pattern with the highest
    proportion of matching values.
    """
    sample = series.dropna().astype(str).head(30)
    if len(sample) == 0:
        return None, 0.0

    best_label, best_ratio = None, 0.0
    for label, pattern in REGEX_PATTERNS.items():
        matches = sum(bool(pattern.match(v.strip())) for v in sample)
        ratio = matches / len(sample)
        if ratio > best_ratio:
            best_label, best_ratio = label, ratio

    return best_label, best_ratio


def detect_pii_columns(df):
    """
    Main entry point. Takes a pandas DataFrame and returns a list of
    dicts describing every column's PII risk:

    [
      {
        "column": "Email",
        "detected": True,
        "label": "Email",
        "confidence": 95,
        "reasons": ["Column name matches keyword 'email'", "92% of values match Email pattern"],
        "sample_values": ["a@x.com", "b@y.com"]
      },
      ...
    ]
    """
    results = []

    for col in df.columns:
        reasons = []
        confidence = 0
        label = None

        # --- rule-based check ---
        keyword_label = _keyword_match(col)
        if keyword_label:
            label = keyword_label
            confidence += 60
            reasons.append(f"Column name suggests '{keyword_label}'")

        # --- regex-based check ---
        regex_label, ratio = _regex_match_ratio(df[col])
        if regex_label and ratio >= 0.5:
            label = label or regex_label
            confidence += int(ratio * 40)
            reasons.append(f"{int(ratio * 100)}% of sampled values match {regex_label} pattern")

        confidence = min(confidence, 100)
        detected = confidence >= 40

        results.append({
            "column": col,
            "detected": detected,
            "label": label or "Unknown",
            "confidence": confidence,
            "reasons": reasons if reasons else ["No sensitive pattern found"],
            "sample_values": [str(v) for v in df[col].dropna().head(3).tolist()],
        })

    return results


def calculate_privacy_risk_score(detected_columns):
    """
    Very simple overall risk score (0-100) based on how many
    high-confidence PII columns exist and how sensitive they are.
    """
    if not detected_columns:
        return 0

    flagged = [c for c in detected_columns if c["detected"]]
    if not flagged:
        return 0

    avg_confidence = sum(c["confidence"] for c in flagged) / len(flagged)
    coverage = len(flagged) / len(detected_columns)
    score = (avg_confidence * 0.7) + (coverage * 100 * 0.3)
    return round(min(score, 100), 1)
