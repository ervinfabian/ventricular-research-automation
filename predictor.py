# import os
# import sys
# from pathlib import Path
# import subprocess

# INPUT_DATA = "/Users/ervin/Documents/kutatas/input/"
# OUTPUT_DATA = "/Users/ervin/Documents/kutatas/output/"
# os.environ["nnUNet_results"] = "/Users/ervin/Documents/kutatas/nnUNet_results"

# NNUNET_PREDICT_BIN = "/Users/ervin/venvs/nnunet/bin/nnUNetv2_predict"

# def run_nnunet_predict_single_case():

#     cmd = [
#         NNUNET_PREDICT_BIN,
#         "-i", INPUT_DATA,
#         "-o", OUTPUT_DATA,
#         "-d", "001",
#         "-c", "3d_fullres",
#         "-f", "0",
#         "-tr", "nnUNetTrainer_20epochs",
#         "-p", "nnUNetPlans"
#     ]

#     subprocess.run(cmd, check=True)

#     if not os.path.exists(output_file):
#         raise RuntimeError(f"Prediction missing: {output_file}")

# run_nnunet_predict_single_case()

import os
import subprocess

INPUT_DATA = "/Users/ervin/Documents/kutatas/input/"
OUTPUT_DATA = "/Users/ervin/Documents/kutatas/output/"

os.environ["nnUNet_raw"] = "/Users/ervin/Documents/kutatas/nnUNet_raw"
os.environ["nnUNet_preprocessed"] = "/Users/ervin/Documents/kutatas/nnUNet_preprocessed"
os.environ["nnUNet_results"] = "/Users/ervin/Documents/kutatas/nnUNet_results"

NNUNET_PREDICT_BIN = "/Users/ervin/venvs/nnunet/bin/nnUNetv2_predict"

def run_nnunet_predict_single_case():
    cmd = [
        NNUNET_PREDICT_BIN,
        "-i", INPUT_DATA,
        "-o", OUTPUT_DATA,
        "-d", "1",  # or Dataset001_XXX
        "-c", "3d_fullres",
        "-f", "0",
        "-tr", "nnUNetTrainer_20epochs",
        "-p", "nnUNetPlans"
    ]

    subprocess.run(cmd, check=True)

run_nnunet_predict_single_case()

