import os
import pathlib
import slicer
import vtk
import ctk
from DICOMLib import DICOMUtils
import time
import SegmentStatistics

## iteration through the file tree
## reading/importing of the CT scans

counter = 0

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
        print(brain_volume/1000)

        counter = counter + 1

   
