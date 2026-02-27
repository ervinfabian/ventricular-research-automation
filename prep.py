import os
import pathlib
import slicer
import vtk
import ctk
from DICOMLib import DICOMUtils
import time
import SegmentStatistics
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
import nibabel as nib
import vtk.util.numpy_support as vtk_np

NNUNET_INFER_ROOT = os.path.expanduser("/home/ervin/Documents/kutatas/ventricular-research-automation/")  # temp working dir
NNUNET_INPUT_DIR = os.path.join(NNUNET_INFER_ROOT, "input")
NNUNET_OUTPUT_DIR = os.path.join(NNUNET_INFER_ROOT, "output")


def export_volume_to_nifti(volume_node, out_path_nii_gz: str):
    slicer.util.saveNode(volume_node, out_path_nii_gz)

## google sheet access
SERVICE_ACCOUNT_JSON_LINUX = "/home/ervin/Documents/kutatas/ventricular-research-automation/brain-ventricles-study-7b0925fa71d3.json"
SERVICE_ACCOUNT_JSON_MACOS = "/Users/ervin/Documents/kutatas/brain-ventricles-study-7b0925fa71d3.json"
SPREADSHEET_ID = "1VXfUrSS3qPuWkplbNVOstrAWffUUlibHoNcKlxBQLuE"
WORKSHEET_NAME = "Original-data"


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_age_sex_from_patient(patient_uid: str):
    db = slicer.dicomDatabase

    studies = db.studiesForPatient(patient_uid)
    if not studies:
        return None, None

    series = db.seriesForStudy(studies[0])
    if not series:
        return None, None

    instances = db.instancesForSeries(series[0])
    if not instances:
        return None, None

    sop_uid = instances[0]

    age = db.instanceValue(sop_uid, "0010,1010")  # PatientAge
    sex = db.instanceValue(sop_uid, "0010,0040")  # PatientSex

    # optional: convert age to integer years
    age_years = None
    if age and age.endswith("Y"):
        try:
            age_years = int(age[:3])
        except Exception:
            pass

    return age_years, sex

def get_ws():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON_LINUX, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh.get_worksheet(0)

def append_case(case_id: str, sex: str, age: int, brain_volume: float, width: float, slice: int):
    ws = get_ws()
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ws.append_row([case_id, sex, age, brain_volume, width, slice, ts], value_input_option="USER_ENTERED")


def get_slicer_max_skull_width(volume_input):
    # Ellenőrizzük, hogy a bemenet szöveg-e vagy már egy objektum
    if isinstance(volume_input, str):
        volume_node = slicer.util.getNode(volume_input)
    else:
        volume_node = volume_input

    if not volume_node:
        print("Hiba: A megadott kötet nem található!")
        return

    # Adatok kinyerése
    data = slicer.util.arrayFromVolume(volume_node)
    spacing = volume_node.GetSpacing()
    
    max_width_mm = 0
    best_slice = 0

    # Pásztázás az axiális szeleteken
    for z in range(data.shape[0]):
        slice_2d = data[z, :, :]
        coords = np.argwhere(slice_2d > 0)
        
        if coords.size > 0:
            # Slicer/Numpy tengelyek: data[Z, Y, X] -> coords[:, 1] az X (szélesség)
            width_pixels = np.max(coords[:, 1]) - np.min(coords[:, 1])
            width_mm = width_pixels * spacing[0]
            
            if width_mm > max_width_mm:
                max_width_mm = width_mm
                best_slice = z

    # print(f"--- Eredmény ---")
    # print(f"Kötet neve: {volume_node.GetName()}")
    # print(f"Maximális koponya szélesség: {max_width_mm:.2f} mm")
    # print(f"Szelet index: {best_slice}")
    
    return max_width_mm, best_slice


## iteration through the file tree
## reading/importing of the CT scans
linux_path = "/home/ervin/Documents/kutatas/ventricular-research-automation/anonym_data/"
macos_path = "/Users/ervin/Documents/kutatas/anonym_data/"
counter = 0

patientUIDs = []

with DICOMUtils.TemporaryDICOMDatabase() as db:
    slicer.util.selectModule("DICOM")
    dicomBrowser = slicer.modules.DICOMWidget.browserWidget.dicomBrowser
    for i in os.listdir(linux_path):
        if not i.startswith('.'):
            dicomBrowser.importDirectory(linux_path + i + "/", dicomBrowser.ImportDirectoryAddLink)
            dicomBrowser.waitForImportFinished()
            print(i)
            print(db.patients()[-1])

## loading into nodes                     
    patientUIDs = db.patients() 
    if not patientUIDs:
        raise RuntimeError("No patients found after import.")  
                        
    for patientUID in patientUIDs:
        loadedNodeID = DICOMUtils.loadPatientByUID(patientUID)
        nodes = [slicer.mrmlScene.GetNodeByID(nid) for nid in loadedNodeID]
        volumes = [n for n in nodes if n and n.IsA("vtkMRMLScalarVolumeNode")]
        # print(volumes[0])

## creating the volume
        ctVolume = slicer.mrmlScene.GetNodeByID(str(loadedNodeID))
    #     volumeNodes = [nod for nod in nodes if nod and nod.IsA("vtkMRMLScalarVolumeNode")]

## swiss skull stripper
        params = {
        "patientVolume": volumes[0].GetID(),
        "patientOutputVolume": slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLScalarVolumeNode", "BrainOnly" + str(counter)
        ),
        "patientMaskLabel": slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "BrainMask" + str(counter)
        ),
        }
        cliNode = slicer.cli.runSync(
        slicer.modules.swissskullstripper,
        None,
        params
        )


## segmentation
        brainVolume = slicer.util.getNode("BrainOnly" + str(counter))
        segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation" + str(counter))
        segNode.CreateDefaultDisplayNodes()
        segNode.SetReferenceImageGeometryParameterFromVolumeNode(brainVolume)

        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)

        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)

        segmentEditorWidget.setSegmentationNode(segNode)
        segmentEditorWidget.setSourceVolumeNode(brainVolume)

        # Add a segment
        segId = segNode.GetSegmentation().AddEmptySegment("ThresholdSeg" + str(counter))
        segmentEditorWidget.setCurrentSegmentID(segId)

        # Apply threshold
        segmentEditorWidget.setActiveEffectByName("Threshold")
        effect = segmentEditorWidget.activeEffect()

        effect.setParameter("MinimumThreshold", "1")   # <-- choose your HU range
        effect.setParameter("MaximumThreshold", "46")    # <-- choose your HU range
        effect.self().onApply()

        # Apply smoothing
        segmentEditorWidget.setActiveEffectByName("Smoothing")
        effect = segmentEditorWidget.activeEffect()

        effect.setParameter("SmoothingMethod", "MORPHOLOGICAL_CLOSING")
        effect.setParameter("KernelSizeMm", "1.5")  # <-- 4 mm smoothing
        effect.self().onApply()

        # masking outside
        
        labelmapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "ValidationMask")
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(segNode, [segId], labelmapNode, volumes[0])

        ctArray = slicer.util.arrayFromVolume(volumes[0])
        maskArray = slicer.util.arrayFromVolume(labelmapNode)
        import scipy.ndimage
        # This fills any 0-value holes inside your 1-value segment
        maskArray[:] = scipy.ndimage.binary_fill_holes(maskArray)

        resultArray = np.copy(ctArray).astype(np.float32)
        
        resultArray[maskArray == 0] = -10000.0

        theBrain = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "TheBrain" + str(counter))  ## it will be the volume of the segmented Brain
        slicer.util.updateVolumeFromArray(theBrain, resultArray)

        theBrain.SetOrigin(volumes[0].GetOrigin())
        theBrain.SetSpacing(volumes[0].GetSpacing())
        ijkToRas = vtk.vtkMatrix4x4()
        volumes[0].GetIJKToRASMatrix(ijkToRas)
        theBrain.SetIJKToRASMatrix(ijkToRas)


        # run Segment Statistics
        logic = SegmentStatistics.SegmentStatisticsLogic()
        paramNode = logic.getParameterNode()
        paramNode.SetParameter("Segmentation", segNode.GetID())
        paramNode.SetParameter("ScalarVolume", theBrain.GetID())
        logic.computeStatistics()

        case_id = f"case_{counter}"
        input_path = os.path.join(NNUNET_INPUT_DIR, f"{case_id}_0000.nii.gz")

        export_volume_to_nifti(theBrain, input_path)

        stats = logic.getStatistics()

        brain_volume = stats[(segId, "LabelmapSegmentStatisticsPlugin.volume_mm3")] ## the calculated brain volume
        age, sex = get_age_sex_from_patient(patientUID)
        needed_width = get_slicer_max_skull_width(theBrain)
        print(needed_width)
        append_case(patientUID, sex, age, brain_volume, needed_width[0], needed_width[1])

        counter = counter + 1

   
