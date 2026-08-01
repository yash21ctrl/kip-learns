"""
Training Data Cleaner v2 — Pure Python Version (Zero dependencies required)
"""

import csv
import os

INPUT_CSV = "training_sessions.csv"
OUTPUT_CSV_CLEANED = "training_sessions_cleaned.csv"
OUTPUT_CSV_RELABELED = "training_sessions_relabeled.csv"

if not os.path.exists(INPUT_CSV):
    raise FileNotFoundError(f"Input file {INPUT_CSV} not found!")

with open(INPUT_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

if not rows:
    raise ValueError("Input CSV is empty!")

required_cols = ["retry_count", "time_taken", "tab_switches", "mouse_idle_time",
                  "typing_pauses", "used_visual_toggle", "frustration_label", "subject"]
missing = [c for c in required_cols if c not in rows[0]]
if missing:
    raise ValueError(f"Missing expected columns: {missing}.")

def score_to_label(score):
    if score <= 2:
        return "Low"
    elif score <= 6:
        return "Medium"
    else:
        return "High"

label_rank = {"Low": 0, "Medium": 1, "High": 2}

processed_rows = []
math_struggle_counts = {"Dyscalculia-pattern": 0, "ADHD-pattern": 0, "Mixed/Unclear": 0}

agree = 0
close = 0
bad = 0
total = len(rows)

for r in rows:
    retry_count = float(r["retry_count"])
    time_taken = float(r["time_taken"])
    tab_switches = float(r["tab_switches"])
    mouse_idle_time = float(r["mouse_idle_time"])
    typing_pauses = float(r["typing_pauses"])
    used_visual_toggle = int(r["used_visual_toggle"]) if str(r["used_visual_toggle"]).isdigit() else (1 if str(r["used_visual_toggle"]).lower() in ["true", "1"] else 0)
    subject = str(r["subject"]).strip()
    frustration_label = str(r["frustration_label"]).strip()

    # ADHD Signal
    adhd_signal = 0.0
    adhd_signal += tab_switches * 2.0
    if mouse_idle_time > 8:
        adhd_signal += 1.5
    if mouse_idle_time > 15:
        adhd_signal += 1.0

    is_math = subject.lower() == "math"

    if is_math:
        dyscalculia_signal = 0.0
        dyscalculia_signal += min(retry_count, 5) * 2.0
        if typing_pauses > 4:
            dyscalculia_signal += 1.5
        if used_visual_toggle and retry_count >= 2:
            dyscalculia_signal += 2.0

        if dyscalculia_signal > adhd_signal:
            struggle_type = "Dyscalculia-pattern"
            combined_score = dyscalculia_signal
        elif adhd_signal > dyscalculia_signal:
            struggle_type = "ADHD-pattern"
            combined_score = adhd_signal
        else:
            struggle_type = "Mixed/Unclear"
            combined_score = max(adhd_signal, dyscalculia_signal)
            
        math_struggle_counts[struggle_type] += 1
    else:
        dyscalculia_signal = None
        struggle_type = "ADHD-pattern" if adhd_signal > 0 else "None"
        combined_score = adhd_signal

    objective_label = score_to_label(combined_score)
    self_rank = label_rank.get(frustration_label, 0)
    obj_rank = label_rank.get(objective_label, 0)
    rank_gap = abs(self_rank - obj_rank)

    if rank_gap == 0:
        agree += 1
    elif rank_gap == 1:
        close += 1
    else:
        bad += 1

    r["adhd_signal"] = round(adhd_signal, 2)
    r["dyscalculia_signal"] = round(dyscalculia_signal, 2) if dyscalculia_signal is not None else ""
    r["struggle_type"] = struggle_type
    r["combined_score"] = round(combined_score, 2)
    r["objective_label"] = objective_label
    r["rank_gap"] = rank_gap
    processed_rows.append(r)

print(f"Total rows: {total}")
print(f"Fully agree (trustworthy): {agree} ({agree/total*100:.1f}%)")
print(f"One step off (acceptable): {close} ({close/total*100:.1f}%)")
print(f"Complete disagreement (unreliable): {bad} ({bad/total*100:.1f}%)")

print("\nStruggle type breakdown (Math questions only):")
for k, v in math_struggle_counts.items():
    print(f"  {k}: {v}")

keep_cols = ["retry_count", "time_taken", "tab_switches", "mouse_idle_time",
             "typing_pauses", "used_visual_toggle", "subject", "frustration_label", "struggle_type"]

# Save cleaned version
cleaned_rows = [r for r in processed_rows if r["rank_gap"] <= 1]
with open(OUTPUT_CSV_CLEANED, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=keep_cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(cleaned_rows)
print(f"\nSaved {len(cleaned_rows)} trustworthy rows to {OUTPUT_CSV_CLEANED}")

# Save relabeled version
relabeled_rows = []
for r in processed_rows:
    r_copy = dict(r)
    r_copy["frustration_label"] = r_copy["objective_label"]
    relabeled_rows.append(r_copy)

with open(OUTPUT_CSV_RELABELED, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=keep_cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(relabeled_rows)
print(f"Saved {len(relabeled_rows)} relabeled rows to {OUTPUT_CSV_RELABELED}")

print("\n--- RECOMMENDATION ---")
disagreement_ratio = bad / total
if disagreement_ratio > 0.5:
    print(f"More than 50% disagreement ({disagreement_ratio*100:.1f}%) — use {OUTPUT_CSV_RELABELED} to retrain.")
else:
    print(f"Use {OUTPUT_CSV_CLEANED} to train — enough trustworthy rows remain ({len(cleaned_rows)} rows).")
