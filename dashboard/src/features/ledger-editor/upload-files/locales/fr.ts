const frUploadFiles: Record<string, { message: string; description: string }> =
  {
    "ledgerEditor.addFilesViaUpload": {
      message: "Ajouter des fichiers via téléversement",
      description: "Placeholder for commit message when uploading files",
    },
    "ledgerEditor.chooseYourFiles": {
      message: "Choisir vos fichiers",
      description: "Button label to choose files for upload",
    },
    "ledgerEditor.commitMessage": {
      message: "Commentaire de téléversement (facultatif)",
      description: "Label for upload comment field when uploading files",
    },
    "ledgerEditor.dragFilesHere": {
      message:
        "Glissez-déposez des fichiers ici pour les ajouter à votre dépôt",
      description: "Instruction text in drag and drop upload area",
    },
    "ledgerEditor.exceedsFileSizeLimit": {
      message: "Dépasse la limite de 1MB",
      description: "Warning message when file size exceeds the maximum limit",
    },
    "ledgerEditor.removeOversizedFiles": {
      message: "Retirez les fichiers de plus de 1 MB pour les téléverser",
      description:
        "Explains why upload is disabled while oversized files are selected",
    },
    "ledgerEditor.fileAlreadyExists": {
      message: "Existe déjà dans ce dossier",
      description:
        "Shown on a staged upload whose name already exists in the target folder",
    },
    "ledgerEditor.removeExistingFiles": {
      message:
        "Retirez les fichiers qui existent déjà dans ce dossier pour téléverser",
      description:
        "Explains why upload is disabled while staged files already exist in the folder",
    },
    "ledgerEditor.uploadStoppedAt": {
      message: "{fileName} n'a pas été téléversé : {reason}",
      description:
        "Upload error naming the file that failed; {reason} is the localized cause",
    },
    "ledgerEditor.uploadedBeforeFailure": {
      message: "Téléversés et retirés de la liste : {files}",
      description:
        "After a failed upload, lists the files that were uploaded and removed from the staged list",
    },
    "ledgerEditor.maximumFileSize": {
      message: "Taille maximale du fichier : 1MB",
      description: "Maximum file size limit text in upload area",
    },
    "ledgerEditor.or": {
      message: "ou",
      description:
        "Conjunction word between drag and drop and file picker options",
    },
    "ledgerEditor.removeSelectedFile": {
      message: "Supprimer {fileName}",
      description:
        "Aria label for removing a staged upload file; {fileName} is the file name",
    },
    "ledgerEditor.selectedFiles": {
      message: "Fichiers sélectionnés ({count})",
      description:
        "Label for selected files list (contains {count} placeholder)",
    },
    "ledgerEditor.uploading": {
      message: "Téléversement en cours...",
      description: "Message shown during file upload",
    },
  };

export default frUploadFiles;
