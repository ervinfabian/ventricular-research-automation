from __future__ import annotations
import os
import pydicom
from pathlib import Path


# Keep these (you said you need them)
KEEP_TAGS = {
    "PatientAge",
    "PatientSex",
}


# Blank these if present (PHI / site identifiers / dates)
TAGS_TO_BLANK = [
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientAddress",
    "OtherPatientIDs",              # sometimes present (non-retired variant)
    "InstitutionName",
    "InstitutionAddress",
    "ReferringPhysicianName",
    "PerformingPhysicianName",
    "NameOfPhysiciansReadingStudy",
    "OperatorsName",
    "AccessionNumber",
    "StudyID",
    "StationName",
    "StudyDescription",
    "SeriesDescription",
    "ProtocolName",
    "StudyDate",
    "SeriesDate",
    "AcquisitionDate",
    "ContentDate",
    "StudyTime",
    "SeriesTime",
    "AcquisitionTime",
    "ContentTime",
    "InstanceCreationDate",
    "InstanceCreationTime",
    "PerformedProcedureStepStartDate",
    "PerformedProcedureStepStartTime",
    "PerformedProcedureStepID",
    "PerformedProcedureStepDescription",
]

study_uid_map: dict[str, str] = {}
series_uid_map: dict[tuple[str, str], str] = {}
frame_uid_map: dict[tuple[str, str], str] = {}
irr_uid_map: dict[tuple[str, str], str] = {}


def _get_series_key(ds) -> tuple[str, str] | None:
    if "StudyInstanceUID" not in ds or "SeriesInstanceUID" not in ds:
        return None
    return (str(ds.StudyInstanceUID), str(ds.SeriesInstanceUID))


def anonymize_dicom(in_path: Path, out_path: Path, counter: int) -> bool:
    """
    Returns True if file was anonymized & written, False if skipped (not DICOM or read error).
    """
    try:
        ds = pydicom.dcmread(str(in_path), force=True)
    except Exception:
        return False

    # Quick sanity check that it's actually DICOM-ish
    if "SOPClassUID" not in ds or "PixelData" not in ds:
        return False

    # Remove private (vendor) tags
    ds.remove_private_tags()

    # Blank selected PHI tags, but keep age/sex
    for kw in TAGS_TO_BLANK:
        if kw in KEEP_TAGS:
            continue
        if kw in ds:
            ds.data_element(kw).value = ""

    # Also blank the retired tag you showed explicitly (if present)
    # (0010,1000) RETIRED_OtherPatientIDs
    retired_other_ids = (0x0010, 0x1000)
    if retired_other_ids in ds:
        ds[retired_other_ids].value = ""

    # --- CHANGED: replace UIDs per SERIES (not per file) ---
    key = _get_series_key(ds)
    if key is not None:
        old_study_uid, old_series_uid = key

        if old_study_uid not in study_uid_map:
            study_uid_map[old_study_uid] = pydicom.uid.generate_uid()
        if key not in series_uid_map:
            series_uid_map[key] = pydicom.uid.generate_uid()

        ds.StudyInstanceUID = study_uid_map[old_study_uid]
        ds.SeriesInstanceUID = series_uid_map[key]

        if "FrameOfReferenceUID" in ds:
            if key not in frame_uid_map:
                frame_uid_map[key] = pydicom.uid.generate_uid()
            ds.FrameOfReferenceUID = frame_uid_map[key]

        if "IrradiationEventUID" in ds:
            if key not in irr_uid_map:
                irr_uid_map[key] = pydicom.uid.generate_uid()
            ds.IrradiationEventUID = irr_uid_map[key]

    # SOPInstanceUID must be unique per FILE/instance
    if "SOPInstanceUID" in ds:
        ds.SOPInstanceUID = pydicom.uid.generate_uid()

    # (Optional but common) Replace PatientName with ANON rather than blank
    if "PatientName" in ds:
        ds.PatientName = "ANONYM"
    
    if "PatientID" in ds:
        ds.PatientID = str(counter)

    # Ensure output directory exists and write
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ds.save_as(str(out_path))
    # print(ds.PatientAge)
    # print(ds.PatientName)
    # print(ds.PatientSex)

    return True

def anonymize_tree(input_root: Path, output_root: Path) -> None:
    input_root = input_root.resolve()
    output_root = output_root.resolve()

    total = 0
    written = 0
    skipped = 0
    count = 1
    
    counter = 0
    for dirpath, _, filenames in os.walk(input_root):
        dirpath_p = Path(dirpath)
        

        if count % 4 == 0:
            rel_dir = Path("case" + str(counter))
            print(counter)
            file_counter = 0
            for fn in filenames:
                filename = "file" + str(file_counter)
                total += 1
                in_file = dirpath_p / fn

                # Mirror the directory structure under output_root
                out_file = output_root / rel_dir / filename
                ok = anonymize_dicom(in_file, out_file, counter)
                if ok:
                    written += 1       
                else:
                    skipped += 1
                
                file_counter = file_counter + 1
            counter = counter + 1

        count = count + 1

    print(f"Done. Total files seen: {total}")
    print(f"Anonymized & written: {written}")
    print(f"Skipped (not DICOM / error): {skipped}")
    print(f"Output folder: {output_root}")

if __name__ == "__main__":
    # EDIT THESE TWO PATHS
    INPUT_ROOT = Path("/home/ervin/Documents/kutatas/ventricular-research-automation/data/")     # e.g. "/home/you/raw_dicoms"
    OUTPUT_ROOT = Path("/home/ervin/Documents/kutatas/ventricular-research-automation/anonym_data/")     # e.g. "/home/you/anon_dicoms"
    anonymize_tree(INPUT_ROOT, OUTPUT_ROOT)
    
    # print(INPUT_ROOT.resolve())
    # print(OUTPUT_ROOT.resolve())


