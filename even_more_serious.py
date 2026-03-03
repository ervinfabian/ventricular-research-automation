import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_curve, auc

INPUT = "data_cleaned.csv"

df = pd.read_csv(INPUT)

# =====================================================
# 0. PREP
# =====================================================

# sex binarizálás
if "sex" in df.columns:
    df["sex_bin"] = df["sex"].str.upper().map({"M": 1, "F": 0})

# hydrocephalus proxy (klasszikus cutoff)
df["ei_ge_030"] = (df["evans_index"] >= 0.30).astype(int)

num_cols = [
    "evans_index",
    "brain",
    "lateral_ventricle",
    "third_ventricle",
    "fourth_ventricle",
    "subarachnoid",
    "age",
]

# =====================================================
# 1. SPEARMAN TABLE (publication ready)
# =====================================================

rows = []

for col in num_cols:
    if col == "evans_index":
        continue

    tmp = df[["evans_index", col]].dropna()
    if len(tmp) > 10:
        rho, p = spearmanr(tmp["evans_index"], tmp[col])
        rows.append({
            "Variable": col,
            "Spearman_rho": rho,
            "p_value": p,
            "N": len(tmp)
        })

spearman_table = pd.DataFrame(rows)
spearman_table.to_csv("spearman_results.csv", index=False)

print("\n==== SPEARMAN TABLE ====")
print(spearman_table.round(4))

# =====================================================
# 2. MULTIVARIÁNS REGRESSZIÓ
# =====================================================

features = [
    "age",
    "sex_bin",
    "lateral_ventricle",
    "third_ventricle",
    "fourth_ventricle",
    "subarachnoid",
]

model_df = df[features + ["evans_index"]].dropna()

X = model_df[features]
y = model_df["evans_index"]

# standardizálás → standardizált beta
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

reg = LinearRegression()
reg.fit(X_scaled, y)

beta_table = pd.DataFrame({
    "Variable": features,
    "Standardized_beta": reg.coef_
})

beta_table.to_csv("regression_betas.csv", index=False)

print("\n==== STANDARDIZED BETAS ====")
print(beta_table.round(4))

print(f"\nR^2 = {reg.score(X_scaled, y):.4f}")

# =====================================================
# 3. ROC ANALÍZIS
# =====================================================

# prediktor: lateral ventricle volume (leggyakoribb biomarker)
roc_df = df[["ei_ge_030", "lateral_ventricle"]].dropna()

fpr, tpr, thresholds = roc_curve(
    roc_df["ei_ge_030"],
    roc_df["lateral_ventricle"]
)

roc_auc = auc(fpr, tpr)

print(f"\nAUC (lateral ventricle → EI≥0.30): {roc_auc:.4f}")

# ROC plot
plt.figure(figsize=(5,5))
plt.plot(fpr, tpr, label=f"AUC = {roc_auc:.3f}")
plt.plot([0,1], [0,1], linestyle="--")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC: Lateral ventricle vs EI≥0.30")
plt.legend()
plt.tight_layout()
plt.savefig("roc_lateral_vs_ei030.png", dpi=300)
plt.close()

# =====================================================
# 4. PUBLICATION SCATTER
# =====================================================

plt.figure(figsize=(5,4))
plt.scatter(df["lateral_ventricle"], df["evans_index"])
plt.xlabel("Lateral ventricle volume")
plt.ylabel("Evans index")
plt.title("Association between EI and lateral ventricle volume")
plt.tight_layout()
plt.savefig("ei_vs_lateral.png", dpi=300)
plt.close()

print("\n✅ JOURNAL-READY STAT CSOMAG KÉSZ")