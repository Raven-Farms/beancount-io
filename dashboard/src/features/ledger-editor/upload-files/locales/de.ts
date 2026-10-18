const deUploadFiles: Record<string, { message: string; description: string }> =
  {
    "ledgerEditor.addFilesViaUpload": {
      message: "Dateien über Upload hinzufügen",
      description: "Placeholder for commit message when uploading files",
    },
    "ledgerEditor.chooseYourFiles": {
      message: "Dateien auswählen",
      description: "Button label to choose files for upload",
    },
    "ledgerEditor.commitMessage": {
      message: "Upload-Kommentar (optional)",
      description: "Label for upload comment field when uploading files",
    },
    "ledgerEditor.dragFilesHere": {
      message:
        "Dateien hierher ziehen, um sie zu Ihrem Repository hinzuzufügen",
      description: "Instruction text in drag and drop upload area",
    },
    "ledgerEditor.exceedsFileSizeLimit": {
      message: "Überschreitet 1MB-Limit",
      description: "Warning message when file size exceeds the maximum limit",
    },
    "ledgerEditor.removeOversizedFiles": {
      message: "Entfernen Sie Dateien über 1 MB, um sie hochzuladen",
      description:
        "Explains why upload is disabled while oversized files are selected",
    },
    "ledgerEditor.fileAlreadyExists": {
      message: "Existiert bereits in diesem Ordner",
      description:
        "Shown on a staged upload whose name already exists in the target folder",
    },
    "ledgerEditor.removeExistingFiles": {
      message:
        "Entfernen Sie Dateien, die in diesem Ordner bereits existieren, um hochzuladen",
      description:
        "Explains why upload is disabled while staged files already exist in the folder",
    },
    "ledgerEditor.uploadStoppedAt": {
      message: "{fileName} wurde nicht hochgeladen: {reason}",
      description:
        "Upload error naming the file that failed; {reason} is the localized cause",
    },
    "ledgerEditor.uploadedBeforeFailure": {
      message: "Hochgeladen und aus der Liste entfernt: {files}",
      description:
        "After a failed upload, lists the files that were uploaded and removed from the staged list",
    },
    "ledgerEditor.maximumFileSize": {
      message: "Maximale Dateigröße: 1MB",
      description: "Maximum file size limit text in upload area",
    },
    "ledgerEditor.or": {
      message: "oder",
      description:
        "Conjunction word between drag and drop and file picker options",
    },
    "ledgerEditor.removeSelectedFile": {
      message: "{fileName} entfernen",
      description:
        "Aria label for removing a staged upload file; {fileName} is the file name",
    },
    "ledgerEditor.selectedFiles": {
      message: "Ausgewählte Dateien ({count})",
      description:
        "Label for selected files list (contains {count} placeholder)",
    },
    "ledgerEditor.uploading": {
      message: "Wird hochgeladen...",
      description: "Message shown during file upload",
    },
  };

export default deUploadFiles;
