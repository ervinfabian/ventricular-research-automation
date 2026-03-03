import nibabel as nib
import numpy as np
import os
import gspread
from datetime import datetime, timezone
from oauth2client.service_account import ServiceAccountCredentials
import scipy.ndimage as ndi


# --- GOOGLE SHEETS SETUP ---
def get_ws():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Cseréld ki a saját json fájlod nevére!
    creds = ServiceAccountCredentials.from_json_keyfile_name("/Users/ervin/Documents/kutatas/brain-ventricles-study-7b0925fa71d3.json", scope)
    client = gspread.authorize(creds)
    # Cseréld ki a saját táblázatod nevére!
    return client.open("Segment-data3").sheet1 

def append_case(case_id, frontal_horn_width, skull_width, evans_index, 
                v_brain, v_lateral, v_3rd, v_4th, v_subarch, slice_idx):
    ws = get_ws()
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    # Az általad kért sorrend és adatok
    row = [
        case_id, 
        frontal_horn_width, 
        skull_width, 
        evans_index, 
        v_brain, 
        v_lateral, 
        v_3rd, 
        v_4th, 
        v_subarch, 
        slice_idx, 
        ts
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")

def get_two_largest_components(mask):
    labeled, num = ndi.label(mask)
    if num == 0:
        return mask

    sizes = ndi.sum(mask, labeled, range(1, num + 1))
    largest_labels = np.argsort(sizes)[-2:] + 1
    return np.isin(labeled, largest_labels)


def compute_slice_width(mask2d, pixdim_x):
    coords = np.argwhere(mask2d)
    if coords.size == 0:
        return 0.0
    return (coords[:, 0].max() - coords[:, 0].min()) * pixdim_x


def robust_evans_width(data, dims, pixdim, y_frac, z_frac):
    """Top-k medián alapú Evans szélesség keresés."""
    widths = []
    zs = []

    y_limit = int(dims[1] * y_frac)
    z_start = int(dims[2] * z_frac)

    vent_mask = (data == 2)

    # morfológiai tisztítás
    vent_mask = ndi.binary_opening(vent_mask, iterations=1)
    vent_mask = ndi.binary_closing(vent_mask, iterations=1)

    # csak a 2 legnagyobb komponens
    vent_mask = get_two_largest_components(vent_mask)

    # anterior maszk
    vent_mask[:, y_limit:, :] = False

    for z in range(z_start, dims[2]):
        w = compute_slice_width(vent_mask[:, :, z], pixdim[0])
        if w > 0:
            widths.append(w)
            zs.append(z)

    if len(widths) == 0:
        return 0.0, -1

    # top-k medián (stabil)
    widths = np.array(widths)
    zs = np.array(zs)

    k = min(5, len(widths))
    idx = np.argsort(widths)[-k:]
    best_width = float(np.median(widths[idx]))
    best_z = int(zs[idx[-1]])

    return best_width, best_z

def process_all_scans(input_folder):
    files = [f for f in os.listdir(input_folder) if f.endswith('.nii.gz')]

    for filename in files:
        path = os.path.join(input_folder, filename)
        try:
            img = nib.load(path)
            data = img.get_fdata()
            pixdim = img.header.get_zooms()
            voxel_vol_cm3 = (pixdim[0] * pixdim[1] * pixdim[2]) / 1000.0
            dims = data.shape

            case_id = filename.split('.')[0]

            # ================================
            # 1. TÉRFOGATOK
            # ================================
            v_brain   = round(np.sum(data == 1) * voxel_vol_cm3, 3)
            v_lateral = round(np.sum(data == 2) * voxel_vol_cm3, 3)
            v_3rd     = round(np.sum(data == 3) * voxel_vol_cm3, 3)
            v_4th     = round(np.sum(data == 4) * voxel_vol_cm3, 3)
            v_subarch = round(np.sum(data == 5) * voxel_vol_cm3, 3)

            # ================================
            # 2. EVANS MÉRÉS (progresszív)
            # ================================
            max_v_w, opt_z = robust_evans_width(
                data, dims, pixdim,
                y_frac=0.42,
                z_frac=0.40
            )

            # fallback 2
            if max_v_w == 0:
                max_v_w, opt_z = robust_evans_width(
                    data, dims, pixdim,
                    y_frac=0.50,
                    z_frac=0.40
                )

            # ================================
            # 3. KOPONYA SZÉLESSÉG
            # ================================
            s_width = 0.0
            if opt_z != -1:
                skull_mask = data[:, :, opt_z] > 0
                if np.any(skull_mask):
                    coords = np.argwhere(skull_mask)
                    s_width = (coords[:, 0].max() - coords[:, 0].min()) * pixdim[0]

            ei = (max_v_w / s_width) if s_width > 0 else 0.0

            # ================================
            # 4. HARMADIK FALLBACK (kicsi EI)
            # ================================
            quality_flag = "OK"

            if ei < 0.20:
                quality_flag = "LOW_EI_FALLBACK"

                max_v_w3, opt_z3 = robust_evans_width(
                    data, dims, pixdim,
                    y_frac=0.60,
                    z_frac=0.25
                )

                if max_v_w3 > max_v_w and opt_z3 != -1:
                    max_v_w = max_v_w3
                    opt_z = opt_z3

                    skull_mask = data[:, :, opt_z] > 0
                    if np.any(skull_mask):
                        coords = np.argwhere(skull_mask)
                        s_width = (coords[:, 0].max() - coords[:, 0].min()) * pixdim[0]

                    ei = (max_v_w / s_width) if s_width > 0 else 0.0

            ei = round(ei, 4)

            # ================================
            # 5. SHEET FELTÖLTÉS
            # ================================
            append_case(
                case_id=case_id,
                frontal_horn_width=round(max_v_w, 2),
                skull_width=round(s_width, 2),
                evans_index=ei,
                v_brain=v_brain,
                v_lateral=v_lateral,
                v_3rd=v_3rd,
                v_4th=v_4th,
                v_subarch=v_subarch,
                slice_idx=opt_z
            )

            print(f"Sikeresen feltöltve: {case_id}")

        except Exception as e:
            print(f"Hiba a {filename} feldolgozásakor: {e}")

# Indítás
process_all_scans('/Users/ervin/Documents/kutatas/segments')