import pandas as pd
import numpy as np

# ===== 1. Beolvasás =====
INPUT_CSV = "data.csv"
OUTPUT_CSV = "data_cleaned.csv"

df = pd.read_csv(INPUT_CSV)

# ===== 2. Vessző -> pont konverzió =====
# ezek numerikus mezők (age kivételével már jó)
numeric_cols = [
    "frontal_horn",
    "full_width",
    "evans_index",
    "brain",
    "lateral_ventricle",
    "third_ventricle",
    "fourth_ventricle",
    "subarachnoid",
    "slice",
]

for col in numeric_cols:
    df[col] = (
        df[col]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

# ===== 3. Numerikussá alakítás =====
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# age opcionális
df["age"] = pd.to_numeric(df["age"], errors="coerce")

# ===== 4. Hibás sorok törlése =====

# --- Evans index szűrés ---
mask_evans = df["evans_index"].between(0.15, 0.50, inclusive="both")

# --- Slice szűrés ---
mask_slice = df["slice"] >= 20

# --- Negatív értékek tiltása ---
volume_cols = [
    "frontal_horn",
    "full_width",
    "evans_index",
    "brain",
    "lateral_ventricle",
    "third_ventricle",
    "fourth_ventricle",
    "subarachnoid",
    "slice",
]

mask_non_negative = (df[volume_cols] >= 0).all(axis=1)

# --- Kötelező numerikus mezők ne legyenek NaN ---
mask_not_nan = df[volume_cols].notna().all(axis=1)

# ===== 5. Szűrés alkalmazása =====
clean_df = df[
    mask_evans &
    mask_slice &
    mask_non_negative &
    mask_not_nan
].copy()

# ===== 6. Reset index =====
clean_df.reset_index(drop=True, inplace=True)

# ===== 7. Mentés =====
clean_df.to_csv(OUTPUT_CSV, index=False)

# ===== 8. Gyors riport =====
print("Eredeti sorok:", len(df))
print("Tisztított sorok:", len(clean_df))
print("Törölt sorok:", len(df) - len(clean_df))