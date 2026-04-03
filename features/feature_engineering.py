import pandas as pd
import os

input_path = 'data/structural_data.csv'
output_path = 'features/structural_data_processed.csv'

print(f"Loading data from {input_path}...")
df = pd.read_csv(input_path)

# Verify targets exist but isolate them so we don't accidentally leak them
targets = ['health_score', 'RUL_years']
for t in targets:
    if t not in df.columns:
        raise ValueError(f"Target column {t} missing in input data.")

print("Starting Feature Engineering...")

# 1. age_years: Current age of structure
df['age_years'] = 2025 - df['construction_year']

# 2. years_since_inspection: Time elapsed since last inspection
df['years_since_inspection'] = 2025 - df['last_inspection_year']

# 3. load_ratio: Load as fraction of concrete capacity
df['load_ratio'] = df['load_kn'] / (df['concrete_grade_mpa'] * 100)

# 4. stress_index: Combined static and cyclic stress
df['stress_index'] = df['load_ratio'] * (1 + df['cyclic_load_freq'] / 100)

# 5. age_squared: Non-linear age wear factor
df['age_squared'] = df['age_years'] ** 2

# 6. degradation_rate: Physics-informed annual deterioration estimate
df['degradation_rate'] = df['stress_index'] * (df['env_condition'] + 1) * 0.01

# 7. fatigue_index: Cumulative fatigue score over lifetime
df['fatigue_index'] = (df['cyclic_load_freq'] * df['age_years']) / 1000

print(f"Saving processed data to {output_path}...")
os.makedirs('features', exist_ok=True)
df.to_csv(output_path, index=False)

engineered_cols = [
    'age_years', 'years_since_inspection', 'load_ratio', 
    'stress_index', 'age_squared', 'degradation_rate', 'fatigue_index'
]

print("\nEngineered Feature Summary:")
print(df[engineered_cols].describe().round(3).to_string())
print("\nSuccess! Columns strictly constructed without 'health_score' or 'RUL_years'.")
