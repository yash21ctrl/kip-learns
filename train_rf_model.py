import os
import csv
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

CSV_FILE = "training_sessions_cleaned.csv"
MODEL_FILE = "frustration_model.joblib"

def extract_features(row):
    retries = int(float(row.get("retry_count", 0)))
    t_time = max(0.1, float(row.get("time_taken", 0.0)))
    tab_switches = int(float(row.get("tab_switches", 0)))
    mouse_idle = float(row.get("mouse_idle_time", 0.0))
    typing_pauses = int(float(row.get("typing_pauses", 0)))
    used_vt = 1 if str(row.get("used_visual_toggle", 0)).lower() in ["true", "1"] else 0
    
    idle_ratio = round(mouse_idle / t_time, 3)
    retry_density = round(retries / t_time, 3)
    
    return [
        retries,
        t_time,
        tab_switches,
        mouse_idle,
        typing_pauses,
        used_vt,
        idle_ratio,
        retry_density
    ]

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File {CSV_FILE} not found!")
        return

    data = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("frustration_label") in ["Low", "Medium", "High"]:
                data.append(row)

    print(f"Loaded {len(data)} session telemetry records.")

    label_map = {"Low": 0, "Medium": 1, "High": 2}
    X = [extract_features(r) for r in data]
    y = [label_map[r["frustration_label"]] for r in data]

    feature_names = [
        "retry_count", "time_taken", "tab_switches", "mouse_idle_time",
        "typing_pauses", "used_visual_toggle", "idle_ratio", "retry_density"
    ]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42,
        class_weight="balanced"
    )
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print("\n==============================================")
    print("RANDOM FOREST CLASSIFIER RETRAINING RESULTS")
    print("==============================================")
    print(f"Training set size: {len(X_train)} samples")
    print(f"Testing set size:  {len(X_test)} samples")
    print(f"Held-Out Test Accuracy: {acc * 100:.2f}%")
    print("----------------------------------------------")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Low", "Medium", "High"]))

    importances = dict(zip(feature_names, [round(val, 3) for val in rf.feature_importances_]))
    print("\nFeature Importances:")
    for k, v in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {k}: {v * 100:.1f}%")

    joblib.dump(rf, MODEL_FILE)
    print(f"\nSuccessfully saved retrained model to {MODEL_FILE}!")

if __name__ == "__main__":
    main()
