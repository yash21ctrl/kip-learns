# CALM (Cognitive Adaptive Learning Model) — System Architecture & Implementation Report

---

## Executive Summary

**CALM** is a specialized, neurodivergent-friendly adaptive learning platform engineered to support students with **ADHD (Attention Deficit Hyperactivity Disorder)** and **Dyscalculia (Mathematical Learning Disability)**. 

Unlike standard learning apps that rely on binary right/wrong scores, CALM captures **implicit digital behavioral telemetry** (idle times, tab switches, typing pauses, retries, visual scaffold toggles) and processes it through a **3-Layer Adaptive AI Engine** to detect student cognitive friction, deliver targeted visual scaffolding, and launch physical/mindfulness reset breaks.

---

## 1. Neurodivergent Cognitive Profiling

The system targets two distinct neurodivergent learning profiles:

### A. ADHD (Attention Deficit & Executive Dysfunction)
* **Digital Biomarkers**: High `tab_switches` (off-task surfing), high `mouse_idle_time` (drifting focus), rapid wrong clicks (< 2.0s, impulsive guessing).
* **Intervention**: **Reset Takeover Missions** (5-second physical stretch, breathing exercise, or silly humor break) to restore dopamine levels and reset executive function.

### B. Dyscalculia (Math Learning Disability & Calculation Anxiety)
* **Digital Biomarkers**: High `retry_count` on math sub-topics (e.g., Fractions), long `typing_pauses` on numeric inputs, usage of `used_visual_toggle`.
* **Intervention**: **Visual Scaffolding & Targeted Routing**—converts abstract numbers into visual fraction bars/pie blocks and steps down difficulty *within the same sub-topic*.

---

## 2. Machine Learning Model (Layer 1) & Dataset Transparency

### A. Telemetry Dataset Split (Transparent Breakdown)
To ensure complete scientific transparency, the training dataset distribution is explicitly structured as follows:

$$\text{Total Records: 801} = \underbrace{287 \text{ Real Student Telemetry Logs (36\%)}}_{\text{Empirical Classmate Data}} + \underbrace{514 \text{ Synthetic Profile Extensions (64\%)}}_{\text{Custom Synthetic Behavior Simulator with Per-Profile Variation}}$$

* **Why Synthetic Data was used**: Real classmate telemetry was heavily skewed toward neurotypical baseline behavior. Synthetic data was generated using a custom synthetic behavior simulator with per-profile variation to balance underrepresented minority profiles (specifically severe Dyscalculia calculation paralysis and ADHD distraction bursts).

### B. Subject-Aware Data Cleaning (Data Cleaner v2)
To eliminate self-reported noise from rushed/lazy labeling during data collection:
* We processed the 801 rows through `clean_training_data.py` (v2 subject-aware, dual-signal cleaner).
* **Subject Differentiation**: Evaluated `dyscalculia_signal` exclusively on **Math** questions (numeric calculation paralysis & visual toggle usage under retry friction) while evaluating `adhd_signal` (tab switches & idle time spikes) across all subjects.
* **Filtering Noise**: The cleaner identified **113 rows (14.1%)** of severe, complete disagreement (rushed/lazy self-labeling). Filtering these out preserved **688 clean, trustworthy rows** (`training_sessions_cleaned.csv`).

### C. Scientific Rejection of Circular Relabeling
> **Methodological Decision**: We explicitly **rejected training on formula-relabeled data (`training_sessions_relabeled.csv`)**. Replacing human self-reports with formulaic labels creates **circular target leakage**—where the model simply learns to reverse-engineer a hand-written python equation rather than learning real human cognitive behavior.

### D. Authentic Model Architecture & XAI Performance
* **Dataset Used**: `training_sessions_cleaned.csv` (688 rows of authentic human self-reported labels with 14.1% severe noise removed).
* **Algorithm**: `DecisionTreeClassifier(max_depth=3)` saved to `frustration_model.joblib`.
* **Single Reproducible Test Accuracy**: **52.17% Accuracy** on a 70/30 held-out test split (207 test samples, 100% reproducible with fixed seed `random_state=42` and `class_weight='balanced'`). This represents an authentic, hard-won, and defensible benchmark on subjective, noisy human frustration.
* **Explainable AI (XAI) Tree Structure**:
  ```text
  |--- mouse_idle_time <= 5.62s -> Low Frustration (Flow State)
  |--- mouse_idle_time > 5.62s
  |   |--- retry_count <= 2.5 -> tab_switches > 2.5 -> High Frustration (ADHD Distraction Shift)
  |   |--- retry_count >  2.5 -> mouse_idle_time > 9.56 -> High Frustration (Dyscalculia Math Block)
  ```

---

## 3. 3-Layer Adaptive AI Engine (`app.py`)

### Layer 1: Pure Machine Learning Classifier
* Executes `frustration_model.joblib`. Outputs the raw Decision Tree statistical prediction without hardcoded pre-filters.

### Layer 2: LLM Cognitive Auditor (Gemini LLM)
* **Role**: Acts as a genuine cognitive auditor cross-examining Layer 1's prediction against raw telemetry and human intent.
* **Model**: Dynamic fallback loop (`gemini-2.0-flash` -> `gemini-flash-latest` -> `gemini-2.0-flash-lite` -> `gemini-1.5-flash`).

#### 💡 Real Example of Layer 1 vs Layer 2 Disagreement (Where Layer 2 Won):
> **Scenario**: A student spent 14 seconds idle on a question and submitted a wrong answer once.
> 
> * **Layer 1 (Decision Tree)**: Saw `mouse_idle_time = 14s` and `retry_count = 1` $\rightarrow$ Predicted **"High Frustration"**.
> * **Layer 2 (Gemini LLM Auditor)**: Audited the context—the question text was a long 180-character reading passage (`q_text`), and the student was actively attempting the problem. Gemini reasoned: *"14 seconds is normal reading time for a long passage, not cognitive paralysis."* Gemini **overrode Layer 1 from High down to Medium**, preventing an intrusive reset takeover modal from interrupting the student!

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
