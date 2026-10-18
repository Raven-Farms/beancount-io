const caUploadFiles: Record<string, { message: string; description: string }> =
  {
    "ledgerEditor.addFilesViaUpload": {
      message: "Afegir fitxers mitjançant pujada",
      description: "Placeholder for commit message when uploading files",
    },
    "ledgerEditor.chooseYourFiles": {
      message: "Trieu els fitxers",
      description: "Button label to choose files for upload",
    },
    "ledgerEditor.commitMessage": {
      message: "Comentari de pujada (opcional)",
      description: "Label for upload comment field when uploading files",
    },
    "ledgerEditor.dragFilesHere": {
      message: "Arrossegueu fitxers aquí per afegir-los al vostre repositori",
      description: "Instruction text in drag and drop upload area",
    },
    "ledgerEditor.exceedsFileSizeLimit": {
      message: "Supera el límit de 1MB",
      description: "Warning message when file size exceeds the maximum limit",
    },
    "ledgerEditor.removeOversizedFiles": {
      message: "Elimineu els fitxers de més d'1 MB per pujar-los",
      description:
        "Explains why upload is disabled while oversized files are selected",
    },
    "ledgerEditor.fileAlreadyExists": {
      message: "Ja existeix en aquesta carpeta",
      description:
        "Shown on a staged upload whose name already exists in the target folder",
    },
    "ledgerEditor.removeExistingFiles": {
      message:
        "Traieu els fitxers que ja existeixen en aquesta carpeta per pujar-los",
      description:
        "Explains why upload is disabled while staged files already exist in the folder",
    },
    "ledgerEditor.uploadStoppedAt": {
      message: "{fileName} no s'ha pujat: {reason}",
      description:
        "Upload error naming the file that failed; {reason} is the localized cause",
    },
    "ledgerEditor.uploadedBeforeFailure": {
      message: "Pujats i trets de la llista: {files}",
      description:
        "After a failed upload, lists the files that were uploaded and removed from the staged list",
    },
    "ledgerEditor.maximumFileSize": {
      message: "Mida màxima del fitxer: 1MB",
      description: "Maximum file size limit text in upload area",
    },
    "ledgerEditor.or": {
      message: "o",
      description:
        "Conjunction word between drag and drop and file picker options",
    },
    "ledgerEditor.removeSelectedFile": {
      message: "Elimina {fileName}",
      description:
        "Aria label for removing a staged upload file; {fileName} is the file name",
    },
    "ledgerEditor.selectedFiles": {
      message: "Fitxers seleccionats ({count})",
      description:
        "Label for selected files list (contains {count} placeholder)",
    },
    "ledgerEditor.uploading": {
      message: "Pujant...",
      description: "Message shown during file upload",
    },
  };

export default caUploadFiles;
