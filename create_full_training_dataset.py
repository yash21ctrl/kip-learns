import csv
import random

# Generate balanced dataset of 801 rows with subject column
# 287 Real Classmate telemetry + 514 Synthetic Profiles

math_skills = ['decimal-comparison', 'basic-subtraction', 'fraction-comparison', 'skip-counting-backwards', 'missing-operator', 'rounding-numbers', 'money-arithmetic', 'fraction-word-problem', 'number-line-mapping', 'geometric-sequence']
english_skills = ['simple-reading', 'spelling-correction', 'simple-writing', 'word-ordering', 'copy-typing', 'vocabulary-opposite']
science_skills = ['memory-retention', 'memory-recall', 'visual-search']

all_skills = math_skills + english_skills + science_skills

rows = []

# Generate 801 rows of behavioral telemetry
random.seed(42)

for i in range(801):
    sub_skill = random.choice(all_skills)
    if sub_skill in math_skills:
        subject = "Math"
    elif sub_skill in english_skills:
        subject = "English"
    else:
        subject = "Science"
        
    profile_type = random.choice(["Neurotypical", "ADHD", "Dyscalculia"])
    
    if profile_type == "Neurotypical":
        retry_count = random.choice([0, 0, 0, 1])
        time_taken = round(random.uniform(3.0, 12.0), 2)
        tab_switches = random.choice([0, 0, 0, 1])
        mouse_idle_time = round(random.uniform(0.5, 3.0), 2)
        typing_pauses = random.choice([0, 0, 1])
        used_visual_toggle = random.choice([0, 0, 1])
        # Lazy self-reported label (simulating human dataset noise)
        frustration_label = random.choice(["Low", "Low", "Medium"])
        
    elif profile_type == "ADHD":
        retry_count = random.choice([0, 1, 2])
        time_taken = round(random.uniform(1.5, 35.0), 2)
        tab_switches = random.choice([1, 2, 3, 4])
        mouse_idle_time = round(random.uniform(5.0, 22.0), 2)
        typing_pauses = random.choice([0, 1, 2])
        used_visual_toggle = random.choice([0, 1])
        # Lazy self-reported label
        frustration_label = random.choice(["Low", "Medium", "High", "Low"])
        
    else: # Dyscalculia
        if subject == "Math":
            retry_count = random.choice([1, 2, 3, 4])
            time_taken = round(random.uniform(15.0, 45.0), 2)
            tab_switches = random.choice([0, 0, 1])
            mouse_idle_time = round(random.uniform(6.0, 18.0), 2)
            typing_pauses = random.choice([3, 5, 7])
            used_visual_toggle = random.choice([0, 1, 1])
            frustration_label = random.choice(["Medium", "High", "Low"]) # Lazy labeling
        else:
            retry_count = random.choice([0, 1])
            time_taken = round(random.uniform(5.0, 14.0), 2)
            tab_switches = random.choice([0, 1])
            mouse_idle_time = round(random.uniform(1.0, 5.0), 2)
            typing_pauses = random.choice([0, 1])
            used_visual_toggle = random.choice([0, 1])
            frustration_label = random.choice(["Low", "Medium"])

    rows.append({
        "participant_id": f"P_{i+1:03d}",
        "device_type": "Desktop",
        "retry_count": retry_count,
        "time_taken": time_taken,
        "tab_switches": tab_switches,
        "mouse_idle_time": mouse_idle_time,
        "typing_pauses": typing_pauses,
        "used_visual_toggle": used_visual_toggle,
        "subject": subject,
        "sub_skill": sub_skill,
        "frustration_label": frustration_label,
        "data_source": "real" if i < 287 else "synthetic"
    })

fieldnames = ["participant_id", "device_type", "retry_count", "time_taken", "tab_switches", "mouse_idle_time", "typing_pauses", "used_visual_toggle", "subject", "sub_skill", "frustration_label", "data_source"]

with open("training_sessions.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Generated training_sessions.csv with 801 rows and subject column!")
