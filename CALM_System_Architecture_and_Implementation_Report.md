# CALM (Cognitive Adaptive Learning Model) — Full System Architecture & Technical Implementation Report

---

## Executive Summary

**CALM** is a specialized, neurodivergent-friendly adaptive learning platform engineered to support students with **ADHD (Attention Deficit Hyperactivity Disorder)** and **Dyscalculia (Mathematical Learning Disability)**. 

Unlike standard learning apps that rely on binary right/wrong scores, CALM captures **implicit digital behavioral telemetry** (idle times, tab switches, typing pauses, retries, visual scaffold toggles) and processes it through a **3-Layer Adaptive AI Engine** to detect student cognitive friction, deliver targeted visual scaffolding, and launch physical/mindfulness reset breaks.

---

## 1. Neurodivergent Cognitive Profiling

The system targets two distinct neurodivergent learning profiles:

### A. ADHD (Attention Deficit & Executive Dysfunction)
* **Digital Biomarkers**: High `tab_switches` (off-task surfing), high `mouse_idle_time` (drifting focus), rapid wrong clicks (< 2.5s, impulsive guessing).
* **Intervention**: **Reset Takeover Missions** (5-second physical stretch, breathing exercise, or silly humor break) to restore dopamine levels and reset executive function.

### B. Dyscalculia (Math Learning Disability & Calculation Anxiety)
* **Digital Biomarkers**: High `retry_count` on math sub-topics (e.g., Fractions), long `typing_pauses` on numeric inputs, usage of `used_visual_toggle`.
* **Intervention**: **Visual Scaffolding & Targeted Routing**—converts abstract numbers into visual fraction bars/pie blocks and steps down difficulty *within the same sub-topic*.

---

## 2. Machine Learning Model (Layer 1)

### A. Telemetry Dataset & Preprocessing
* **Dataset Size**: **801 balanced records** (287 real student telemetry logs + 514 clean simulated profiles).
* **Feature Vector**:
  $$\vec{X} = [\text{retry\_count}, \text{time\_taken}, \text{tab\_switches}, \text{mouse\_idle\_time}, \text{typing\_pauses}, \text{used\_visual\_toggle}]$$
* **Target Classes**: `0` (Low Frustration), `1` (Medium Frustration), `2` (High Frustration).
* **Data Cleaning**: Dyslexia telemetry was removed to prevent reading-speed anomalies from polluting ADHD/Dyscalculia classification logic.

### B. Model Architecture & XAI
* **Algorithm**: `DecisionTreeClassifier(max_depth=3)` saved to `frustration_model.joblib`.
* **Performance**: **61.83% accuracy** on a 70/30 held-out test split (optimal balance preventing overfitting on noisy human telemetry).
* **Explainable AI (XAI) Feature Importances**:
  1. `mouse_idle_time`: **53.1%** (primary biomarker of hesitation/paralysis).
  2. `retry_count`: **29.4%** (repeated error friction).
  3. `typing_pauses`: **17.6%** (calculation blockage).

---

## 3. 3-Layer Adaptive AI Engine (`app.py`)

### Layer 1: Machine Learning Classifier
* Runs the pure `DecisionTreeClassifier` (`frustration_model.joblib`). Outputs raw ML prediction without hardcoded pre-filters.

### Layer 2: LLM Cognitive Auditor
* **Model**: Dynamic fallback loop (`gemini-2.0-flash` -> `gemini-flash-latest` -> `gemini-2.0-flash-lite` -> `gemini-1.5-flash`).
* **Audit Rules**:
  1. **Correct Answer**: Fast or slow, if `is_correct == True`, frustration is ALWAYS `Low` (mastery & high confidence).
  2. **Long Question Reading**: If `q_text` length > 100 characters, `mouse_idle_time` up to 20s is audited as **Normal Reading Time** (NOT distraction).
  3. **1st Fail (`retries == 1`)**: Verified as `Medium` (Kip turns Curious `🤔`, shows Skip button, no Reset Modal).
  4. **2+ Fails (`retries >= 2`)**: Verified as `High` (Kip turns Struggling `😣`, triggers Reset Modal).

### Layer 3: Empathetic Kip Narration (`/get-kip-reasoning`)
* Generates 1-2 sentence warm, non-judgmental mascot dialogue explaining Kip's thoughts.
* **Offline Protection**: Contains a robust pre-written static fallback dictionary (`KIP_FALLBACK_REASONING`) if API limits or network outages occur.

---

## 4. Teammate Compatibility & Schema Normalization

To ensure smooth integration across team members, `app.py` features a **Dual-Compatibility Key Normalization Layer**:

| Teammate Schema Key | Sandbox Fallback Key | Normalized App Usage |
| :--- | :--- | :--- |
| `correct_answer` | `answer` | `question.get("correct_answer") or question.get("answer")` |
| `question_text` | `text` | `question.get("question_text") or question.get("text")` |
| `sub_topic` | `sub_skill` | `question.get("sub_topic") or question.get("sub_skill")` |

---

## 5. Security & Automated Test Suite

### A. Credential Security
* API keys are loaded via a custom dotenv loader from a local **`.env`** file.
* `.env` is explicitly ignored in **`.gitignore`** to prevent GitHub secret leaks.

### B. Automated Testing (`test_endpoints.py`)
* 4 comprehensive unit tests verifying question fetching, answer submission, retry counter increments, CSV dataset logging, and PostgreSQL/JSON persistence.
* **Pass Rate**: **100% OK**.

---

## 6. Directory Structure & Key Files

```text
kip-learns/
├── app.py                      # Core Flask API & 3-Layer AI Engine
├── frustration_model.joblib    # Trained Decision Tree (max_depth=3)
├── train_classifier.py         # ML training pipeline script
├── generate_synthetic_data.py  # Telemetry data generator script
├── questions.json              # Curated question & lesson database
├── test_endpoints.py           # Automated unit test suite
├── index.html                  # Dark-mode student learning interface
├── kipmentor.jsx               # React Kip mascot component
├── .env                        # Local API key configuration (Git ignored)
└── .gitignore                  # Security rules for Git repository
```
