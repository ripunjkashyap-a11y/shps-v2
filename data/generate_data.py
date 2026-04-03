import pandas as pd
import numpy as np
import os

np.random.seed(42)

N = 10000

# Generate 10 raw input columns
structure_id = np.arange(1, N + 1)
construction_year = np.random.randint(1960, 2026, N)
# last_inspection_year must be >= construction_year and within 1990-2025
last_inspection_year = np.maximum(construction_year, np.random.randint(1990, 2026, N))
concrete_grade_mpa = np.random.choice([20, 25, 30, 35, 40, 45, 50], N)
elevation_m = np.random.uniform(0.0, 150.0, N)
load_kn = np.random.uniform(100.0, 5000.0, N)
cyclic_load_freq = np.random.uniform(10.0, 500.0, N)
support_type = np.random.randint(0, 4, N)
env_condition = np.random.randint(0, 7, N)
vibration_mms = np.random.uniform(0.1, 12.0, N)

df = pd.DataFrame({
    'structure_id': structure_id,
    'construction_year': construction_year,
    'last_inspection_year': last_inspection_year,
    'concrete_grade_mpa': concrete_grade_mpa,
    'elevation_m': np.round(elevation_m, 1),
    'load_kn': np.round(load_kn, 1),
    'cyclic_load_freq': np.round(cyclic_load_freq, 1),
    'support_type': support_type,
    'env_condition': env_condition,
    'vibration_mms': np.round(vibration_mms, 2)
})

# Temporary computation for physics-informed targets (as per spec)
age_years = 2025 - df['construction_year']
load_ratio = df['load_kn'] / (df['concrete_grade_mpa'] * 100)
stress_index = load_ratio * (1 + df['cyclic_load_freq'] / 100)

# Build Health Score
# Penalty features mapping inverse proportionality
age_penalty = (age_years / 65.0) * 40
stress_penalty = (stress_index / 15.0) * 40
env_penalty = (df['env_condition'] / 6.0) * 20

health_raw = 100 - (age_penalty + stress_penalty + env_penalty) + np.random.normal(0, 5, N)
df['health_score'] = np.clip(health_raw, 0.0, 100.0).round(1)

# Build RUL (Remaining Useful Life)
# Formula spec: RUL ∝ 1 / (stress_index * vibration_mms^2)
rul_raw = 500.0 / (stress_index * (df['vibration_mms']**2) + 10.0) + np.random.normal(0, 2, N)
df['RUL_years'] = np.clip(rul_raw, 0.0, 50.0).round(1)

# Ensure data directory exists
os.makedirs('data', exist_ok=True)
df.to_csv('data/structural_data.csv', index=False)

print(f"Successfully generated {len(df)} records in data/structural_data.csv")
print("\nDataset Summary:")
print(df.describe()[['health_score', 'RUL_years']].to_string())
print("\nNull counts:")
print(df.isnull().sum())
