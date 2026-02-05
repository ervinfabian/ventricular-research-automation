import os
import pathlib
import slicer
import vtk
import ctk
from DICOMLib import DICOMUtils
import time

## iteration through the file tree
## reading/importing of the CT scans

patientUIDs = []
with DICOMUtils.TemporaryDICOMDatabase() as db:
    slicer.util.selectModule("DICOM")
    dicomBrowser = slicer.modules.DICOMWidget.browserWidget.dicomBrowser
    for i in os.listdir("/Users/ervin/Documents/kutatas/data/"):
        if not i.startswith('.'):
            for k in os.listdir("/Users/ervin/Documents/kutatas/data/" + i + "/"):
                if not k.startswith('.'):
                    for l in os.listdir("/Users/ervin/Documents/kutatas/data/" + i + "/" + k + "/"):
                        if not l.startswith('.'):
                            if not os.path.isdir("/Users/ervin/Documents/kutatas/data/" + i + "/" + k + "/" + l + "/"):
                                raise ValueError("Not a folder: " + "/Users/ervin/Documents/kutatas/data/" + i + "/" + k + "/" + l + "/")
                            dicomBrowser.importDirectory("/Users/ervin/Documents/kutatas/data/" + i + "/" + k + "/" + l + "/", dicomBrowser.ImportDirectoryAddLink)
                            dicomBrowser.waitForImportFinished()                       
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
            "vtkMRMLScalarVolumeNode", "BrainOnly"
        ),
        "patientMaskLabel": slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "BrainMask"
        ),
        }
        cliNode = slicer.cli.runSync(
        slicer.modules.swissskullstripper,
        None,
        params
        )


## segmentation
        brainVolume = slicer.util.getNode("BrainOnly")
        segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation")
        segNode.CreateDefaultDisplayNodes()
        segNode.SetReferenceImageGeometryParameterFromVolumeNode(brainVolume)

        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)

        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)

        segmentEditorWidget.setSegmentationNode(segNode)
        segmentEditorWidget.setMasterVolumeNode(brainVolume)

        # Add a segment
        segNode.GetSegmentation().AddEmptySegment("ThresholdSeg")

        # Apply threshold
        segmentEditorWidget.setActiveEffectByName("Threshold")
        effect = segmentEditorWidget.activeEffect()

        effect.setParameter("MinimumThreshold", "1")   # <-- choose your HU range
        effect.setParameter("MaximumThreshold", "46")    # <-- choose your HU range
        effect.self().onApply()

   
