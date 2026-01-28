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
    for i in os.listdir("/Users/ervin/Downloads/cercetare/data/"):
        if not i.startswith('.'):
            for k in os.listdir("/Users/ervin/Downloads/cercetare/data/" + i + "/"):
                if not k.startswith('.'):
                    for l in os.listdir("/Users/ervin/Downloads/cercetare/data/" + i + "/" + k + "/"):
                        if not l.startswith('.'):
                            if not os.path.isdir("/Users/ervin/Downloads/cercetare/data/" + i + "/" + k + "/" + l + "/"):
                                raise ValueError("Not a folder: " + "/Users/ervin/Downloads/cercetare/data/" + i + "/" + k + "/" + l + "/")
                            dicomBrowser.importDirectory("/Users/ervin/Downloads/cercetare/data/" + i + "/" + k + "/" + l + "/", dicomBrowser.ImportDirectoryAddLink)
                            dicomBrowser.waitForImportFinished()                       
                            print(db.patients()[-1])

## loading into nodes                     
    patientUIDs = db.patients() 
    if not patientUIDs:
        raise RuntimeError("No patients found after import.")  
                        
    for patientUID in patientUIDs:
        loadedNodeID = DICOMUtils.loadPatientByUID(patientUID)

## creating the volume
        ctVolume = slicer.mrmlScene.GetNodeByID(str(loadedNodeID))
    #     volumeNodes = [nod for nod in nodes if nod and nod.IsA("vtkMRMLScalarVolumeNode")]

## swiss skull stripper 
        params = {
        "inputVolume": ctVolume,
        "outputVolume": slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLScalarVolumeNode", "BrainOnly"
        ),
        "outputMask": slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "BrainMask"
        ),
        }
        
        cliNode = slicer.cli.run(
        slicer.modules.swissskullstripper,
        None,
        params,
        wait_for_completion=True
        )
    




## segmentation
        # segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
   
