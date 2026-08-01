import os
import csv
import joblib
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import accuracy_score, classification_report

CSV_CLEANED = "training_sessions_cleaned.csv"
CSV_RELABELED = "training_sessions_relabeled.csv"
MODEL_FILE = "frustration_model.joblib"

def load_csv_data(filepath):
    data = []
    if not os.path.exists(filepath):
        return data
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("frustration_label") in ['Low', 'Medium', 'High']:
                data.append(row)
    return data

def main():
    # Train strictly on CSV_CLEANED (688 rows of real human labels, filtering out 14.1% noise) to avoid circular data leakage.
    csv_file = CSV_CLEANED
    print(f"Loading training dataset from {csv_file}...")
    
    data = load_csv_data(csv_file)
    if not data:
        print(f"ERROR: No valid data in {csv_file}!")
        return

    print(f"Successfully loaded {len(data)} telemetry records for model training.")

    X = []
    y = []
    label_map = {"Low": 0, "Medium": 1, "High": 2}
    reverse_map = {0: "Low", 1: "Medium", 2: "High"}

    for row in data:
        used_vt = 1 if str(row.get("used_visual_toggle", 0)).lower() in ["true", "1"] else 0
        features = [
            int(float(row.get("retry_count", 0))),
            float(row.get("time_taken", 0.0)),
            int(float(row.get("tab_switches", 0))),
            float(row.get("mouse_idle_time", 0.0)),
            int(float(row.get("typing_pauses", 0))),
            used_vt
        ]
        X.append(features)
        y.append(label_map[row["frustration_label"]])

    feature_names = [
        "retry_count", 
        "time_taken", 
        "tab_switches", 
        "mouse_idle_time", 
        "typing_pauses", 
        "used_visual_toggle"
    ]

    # Split 70/30 train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    # Train DecisionTreeClassifier(max_depth=3, class_weight='balanced', random_state=42)
    # class_weight='balanced' ensures all 3 classes (Low, Medium, High) have active representation
    clf = DecisionTreeClassifier(max_depth=3, class_weight='balanced', random_state=42)
    clf.fit(X_train, y_train)

    # Test Accuracy Evaluation
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print("\n==============================================")
    print("DECISION TREE CLASSIFIER RETRAINING RESULTS")
    print("==============================================")
    print(f"Training set size: {len(X_train)} samples")
    print(f"Testing set size:  {len(X_test)} samples")
    print(f"Retrained Test Accuracy: {acc * 100:.2f}%")
    print("----------------------------------------------")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Low", "Medium", "High"]))

    print("\nDecision Tree Rules Structure (Explainable AI):")
    print(export_text(clf, feature_names=feature_names))

    # Save retrained model
    joblib.dump(clf, MODEL_FILE)
    print(f"Successfully saved retrained model to {MODEL_FILE}!")

if __name__ == "__main__":
    main()
