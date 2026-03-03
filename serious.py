import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import shapiro, spearmanr, mannwhitneyu

INPUT = "data_cleaned.csv"

df = pd.read_csv(INPUT)

print("==== ALAP INFO ====")
print(df.shape)
print(df.columns)

# =====================================================
# 1. LEÍRÓ STATISZTIKÁK
# =====================================================

print("\n==== LEÍRÓ STAT ====")
desc_cols = [
    "evans_index",
    "brain",
    "lateral_ventricle",
    "third_ventricle",
    "fourth_ventricle",
    "subarachnoid",
    "age",
]

print(df[desc_cols].describe())

# =====================================================
# 2. NORMALITÁS TESZT (Shapiro)
# =====================================================

print("\n==== NORMALITÁS (Shapiro) ====")

for col in desc_cols:
    series = df[col].dropna()
    if len(series) >= 3 and len(series) <= 5000:
        stat, p = shapiro(series)
        print(f"{col:20s} p={p:.5f}")
    else:
        print(f"{col:20s} kihagyva (N nem megfelelő)")

# =====================================================
# 3. SPEARMAN KORRELÁCIÓK
# =====================================================

print("\n==== SPEARMAN KORRELÁCIÓK (Evans vs minden) ====")

target = "evans_index"

for col in desc_cols:
    if col == target:
        continue
    valid = df[[target, col]].dropna()
    if len(valid) > 10:
        r, p = spearmanr(valid[target], valid[col])
        print(f"Evans vs {col:18s} rho={r:.3f}  p={p:.5f}")

# teljes korrelációs mátrix
print("\n==== TELJES SPEARMAN MÁTRIX ====")
corr = df[desc_cols].corr(method="spearman")
print(corr.round(3))

# =====================================================
# 4. NEMEK KÖZTI KÜLÖNBSÉG (Mann–Whitney)
# =====================================================

print("\n==== NEMEK KÖZTI KÜLÖNBSÉG ====")

if "sex" in df.columns:
    males = df[df["sex"].str.upper() == "M"]
    females = df[df["sex"].str.upper() == "F"]

    if len(males) > 5 and len(females) > 5:
        stat, p = mannwhitneyu(
            males["evans_index"],
            females["evans_index"],
            alternative="two-sided",
        )
        print(f"Evans index M vs F p={p:.5f}")
    else:
        print("Nem elég elemszám nemekhez")

# =====================================================
# 5. OUTLIER DETEKTÁLÁS (IQR)
# =====================================================

print("\n==== OUTLIEREK (IQR) ====")

def count_outliers(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return ((series < lower) | (series > upper)).sum()

for col in desc_cols:
    n_out = count_outliers(df[col].dropna())
    print(f"{col:20s}: {n_out} outlier")

# =====================================================
# 6. ÁBRÁK (publication ready)
# =====================================================

# --- Evans eloszlás ---
plt.figure(figsize=(5,4))
plt.hist(df["evans_index"].dropna(), bins=30)
plt.title("Evans index distribution")
plt.xlabel("Evans index")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig("evans_hist.png", dpi=300)
plt.close()

# --- Evans vs age ---
plt.figure(figsize=(5,4))
plt.scatter(df["age"], df["evans_index"])
plt.title("Evans index vs Age")
plt.xlabel("Age")
plt.ylabel("Evans index")
plt.tight_layout()
plt.savefig("evans_vs_age.png", dpi=300)
plt.close()

# --- boxplot nem szerint ---
if "sex" in df.columns:
    plt.figure(figsize=(5,4))
    df.boxplot(column="evans_index", by="sex")
    plt.title("Evans index by Sex")
    plt.suptitle("")
    plt.tight_layout()
    plt.savefig("evans_by_sex.png", dpi=300)
    plt.close()

print("\n✅ STAT pipeline kész.")