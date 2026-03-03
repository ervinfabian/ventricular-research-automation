import pandas as pd
import numpy as np

df = pd.read_csv("data.csv")

print(df.shape)
print(df.columns.tolist())
df.head()


df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

df.columns.tolist()

if "case_id" in df.columns:
    dup = df.duplicated(subset="case_id").sum()
    print("Duplicate case_id:", dup)

    df = df.drop_duplicates(subset="case_id", keep="first")


numeric_cols = [
    "frontal_horn",
    "full_width"
    "evans_index",
    "brain",
    "lateral_ventricle",
    "third_ventricle",
    "fourth_ventricle",
    "subarachnoid",
    "slice",
    "age"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")



missing = df.isna().sum().sort_values(ascending=False)
print(missing)

# 1. Kényszerítjük a számformátumot
# Megszabadulunk a maradék vesszőktől, és lebegőpontos számmá alakítunk
df["evans_index"] = pd.to_numeric(df["evans_index"].astype(str).str.replace(',', '.'), errors='coerce')
df["frontal_horn"] = pd.to_numeric(df["frontal_horn"].astype(str).str.replace(',', '.'), errors='coerce')
df["full_width"] = pd.to_numeric(df["full_width"].astype(str).str.replace(',', '.'), errors='coerce')
df["brain"] = pd.to_numeric(df["brain"].astype(str).str.replace(',', '.'), errors='coerce')

df["lateral_ventricle"] = pd.to_numeric(df["lateral_ventricle"].astype(str).str.replace(',', '.'), errors='coerce')

df["third_ventricle"] = pd.to_numeric(df["third_ventricle"].astype(str).str.replace(',', '.'), errors='coerce')
df["subarachnoid"] = pd.to_numeric(df["subarachnoid"].astype(str).str.replace(',', '.'), errors='coerce')
df["age"] = pd.to_numeric(df["age"].astype(str).str.replace(',', '.'), errors='coerce')
df["slice"] = pd.to_numeric(df["slice"].astype(str).str.replace(',', '.'), errors='coerce')





# 2. (Opcionális de javasolt) Dobáljuk ki a NaN értékeket (amik nem voltak számok)
# Így a statisztika tiszta lesz
df = df.dropna(subset=["evans_index"])

def range_check(series, low, high):
    return ((series < low) | (series > high)).sum()

checks = {}

if "evans_index" in df:
    checks["ei_out_of_range"] = range_check(df["evans_index"], 0.15, 0.5)

if "age" in df:
    checks["age_out_of_range"] = range_check(df["age"], 0, 110)

if "lateral_ventricle" in df:
    checks["lat_vent_outliers"] = (df["lateral_ventricle"] <= 0).sum()

if "slice" in df:
    checks["slice_nr_negative"] = (df["slice"] < 50).sum()

print(checks)


def iqr_flags(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    return (series < low) | (series > high)

df["ei_outlier_iqr"] = iqr_flags(df["evans_index"])
df["latvent_outlier_iqr"] = iqr_flags(df["lateral_ventricle"])

df["v_csf_total"] = (
    df["lateral_ventricle"] +
    df["third_ventricle"] +
    df["fourth_ventricle"] +
    df["subarachnoid"]
)

df["csf_fraction"] = df["v_csf_total"] / (
    df["v_csf_total"] + df["brain"]
)

df["ei_ge_030"] = df["evans_index"] >= 0.30

print("N cases:", len(df))
print(df[[
    "evans_index",
    "brain",
    "lateral_ventricle",
    "subarachnoid",
    "v_csf_total",
    "age"
]].describe())

df_clean = df[df['evans_index'].between(0.15, 0.5)]
df_clean = df[df['slice'] < 20]
print(df_clean[[
    "evans_index",
    "brain",
    "lateral_ventricle",
    "subarachnoid",
    "v_csf_total",
    "age"
]].describe())
print(df.head(10))
