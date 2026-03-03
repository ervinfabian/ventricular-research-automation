import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_curve, auc

INPUT = "data_cleaned.csv"
df = pd.read_csv(INPUT)

print("\n==== ÚJ BIOMARKEREK ====")

# =====================================================
# 1. ÚJ VÁLTOZÓK
# =====================================================

df["total_csf"] = (
    df["lateral_ventricle"] +
    df["third_ventricle"] +
    df["fourth_ventricle"] +
    df["subarachnoid"]
)

df["csf_brain_ratio"] = df["total_csf"] / df["brain"]
df["subarachnoid_fraction"] = df["subarachnoid"] / df["total_csf"]

# hydro proxy
df["ei_ge_030"] = (df["evans_index"] >= 0.30).astype(int)

# =====================================================
# 2. SPEARMAN – FŐ ELEMZÉS
# =====================================================

print("\n==== EI vs GLOBAL MARKERS ====")

tests = [
    "total_csf",
    "csf_brain_ratio",
    "subarachnoid",
    "subarachnoid_fraction",
    "age"
]

for col in tests:
    tmp = df[["evans_index", col]].dropna()
    rho, p = spearmanr(tmp["evans_index"], tmp[col])
    print(f"EI vs {col:25s} rho={rho:.3f} p={p:.5f}")

# =====================================================
# 3. ROC ÖSSZEHASONLÍTÁS
# =====================================================

print("\n==== ROC ÖSSZEHASONLÍTÁS ====")

predictors = [
    "lateral_ventricle",
    "total_csf",
    "csf_brain_ratio",
    "subarachnoid"
]

roc_rows = []

for col in predictors:
    tmp = df[[col, "ei_ge_030"]].dropna()
    fpr, tpr, _ = roc_curve(tmp["ei_ge_030"], tmp[col])
    roc_auc = auc(fpr, tpr)
    roc_rows.append((col, roc_auc))
    print(f"{col:25s} AUC={roc_auc:.3f}")

# =====================================================
# 4. ATRÓFIA TREND ÉLETKORRAL
# =====================================================

print("\n==== ATRÓFIA vs AGE ====")

tmp = df[["csf_brain_ratio", "age"]].dropna()
rho, p = spearmanr(tmp["csf_brain_ratio"], tmp["age"])
print(f"CSF/brain vs age rho={rho:.3f} p={p:.5f}")