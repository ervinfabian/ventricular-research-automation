import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import roc_curve
from sklearn.preprocessing import StandardScaler

INPUT = "data_cleaned.csv"
df = pd.read_csv(INPUT)

# =====================================================
# 1. SEX IRÁNY MEGHATÁROZÁSA
# =====================================================

print("\n==== SEX IRÁNY ====")

if "sex" in df.columns:
    males = df[df["sex"].str.upper() == "M"]["evans_index"].dropna()
    females = df[df["sex"].str.upper() == "F"]["evans_index"].dropna()

    print(f"Férfi EI medián: {males.median():.4f}")
    print(f"Nő EI medián:   {females.median():.4f}")

# =====================================================
# 2. VIF (multikollinearitás)
# =====================================================

print("\n==== VIF ====")

features = [
    "lateral_ventricle",
    "third_ventricle",
    "fourth_ventricle",
    "subarachnoid",
    "age",
]

tmp = df[features].dropna()

def compute_vif(X):
    vif_list = []
    for i, col in enumerate(X.columns):
        y = X[col]
        X_other = X.drop(columns=[col])
        reg = LinearRegression().fit(X_other, y)
        r2 = reg.score(X_other, y)
        vif = 1 / (1 - r2) if r2 < 0.999 else np.inf
        vif_list.append((col, vif))
    return vif_list

vif_results = compute_vif(tmp)

for name, vif in vif_results:
    print(f"{name:20s} VIF={vif:.2f}")

# =====================================================
# 3. REDUCED MODELL (csak strongest predictor)
# =====================================================

print("\n==== REDUCED MODELL ====")

model_df = df[["evans_index", "lateral_ventricle", "age"]].dropna()

X = model_df[["lateral_ventricle", "age"]]
y = model_df["evans_index"]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

reg = LinearRegression().fit(X_scaled, y)

print("Standardized beták:")
for name, coef in zip(X.columns, reg.coef_):
    print(f"{name:20s} beta={coef:.4f}")

print(f"R^2 = {reg.score(X_scaled, y):.4f}")

# =====================================================
# 4. ÉLETKOR KVARTILISEK
# =====================================================

print("\n==== AGE KVARTILISEK ====")

age_df = df.dropna(subset=["age", "evans_index"]).copy()
age_df["age_q"] = pd.qcut(age_df["age"], 4)

group_stats = age_df.groupby("age_q")["evans_index"].agg(["median", "mean", "count"])
print(group_stats)

# =====================================================
# 5. OPTIMÁLIS EI CUTOFF (Youden)
# =====================================================

print("\n==== OPTIMÁLIS EI CUTOFF ====")

roc_df = df[["evans_index", "lateral_ventricle"]].dropna()

y_true = (roc_df["evans_index"] >= 0.30).astype(int)
scores = roc_df["lateral_ventricle"]

fpr, tpr, thr = roc_curve(y_true, scores)

youden = tpr - fpr
best_idx = np.argmax(youden)

print(f"Optimális threshold (LV volume): {thr[best_idx]:.3f}")
print(f"Szenzitivitás: {tpr[best_idx]:.3f}")
print(f"Specificitás: {1 - fpr[best_idx]:.3f}")