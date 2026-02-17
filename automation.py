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


## google sheet access
SERVICE_ACCOUNT_JSON_LINUX = "/home/ervin/Documents/kutatas/ventricular-research-automation/brain-ventricles-study-7b0925fa71d3.json"
SERVICE_ACCOUNT_JSON_MACOS = "/Users/ervin/Documents/kutatas/brain-ventricles-study-7b0925fa71d3.json"
SPREADSHEET_ID = "1VXfUrSS3qPuWkplbNVOstrAWffUUlibHoNcKlxBQLuE"
WORKSHEET_NAME = "Ventricle-data"

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
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON_MACOS, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh.get_worksheet(0)

def append_case(case_id: str, sex: str, age: int, brain_volume: float):
    ws = get_ws()
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ws.append_row([case_id, sex, age, brain_volume, ts], value_input_option="USER_ENTERED")


## iteration through the file tree
## reading/importing of the CT scans
linux_path = "/home/ervin/Documents/kutatas/ventricular-research-automation/anonym_data/"
macos_path = "/Users/ervin/Documents/kutatas/anonym_data/"
counter = 0

patientUIDs = []

with DICOMUtils.TemporaryDICOMDatabase() as db:
    slicer.util.selectModule("DICOM")
    dicomBrowser = slicer.modules.DICOMWidget.browserWidget.dicomBrowser
    for i in os.listdir(macos_path):
        if not i.startswith('.'):
            dicomBrowser.importDirectory(macos_path + i + "/", dicomBrowser.ImportDirectoryAddLink)
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
        effect.setParameter("KernelSizeMm", "4")  # <-- 4 mm smoothing
        effect.self().onApply()

        # masking outside
        maskLabel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "MaskLabel")

        slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(
        segNode, maskLabel, brainVolume
        )

        theBrain = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "TheBrain" + str(counter))  ## it will be the volume of the segmented Brain

        params = {
            "InputVolume": brainVolume.GetID(),
            "MaskVolume": maskLabel.GetID(),
            "OutputVolume": theBrain.GetID(),
            "FillValue": -10000,
        }

        cliNode = slicer.cli.runSync(slicer.modules.maskscalarvolume, None, params)
        print(cliNode.GetStatusString())
        print(cliNode.GetErrorText())

        # run Segment Statistics
        logic = SegmentStatistics.SegmentStatisticsLogic()
        paramNode = logic.getParameterNode()
        paramNode.SetParameter("Segmentation", segNode.GetID())
        paramNode.SetParameter("ScalarVolume", theBrain.GetID())
        logic.computeStatistics()

        stats = logic.getStatistics()

        brain_volume = stats[(segId, "LabelmapSegmentStatisticsPlugin.volume_mm3")] ## the calculated brain volume
        age, sex = get_age_sex_from_patient(patientUID)
        append_case(patientUID, sex, age, brain_volume)

        counter = counter + 1

   
