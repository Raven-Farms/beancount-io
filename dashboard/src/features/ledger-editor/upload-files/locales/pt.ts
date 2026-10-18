const ptUploadFiles: Record<string, { message: string; description: string }> =
  {
    "ledgerEditor.addFilesViaUpload": {
      message: "Adicionar arquivos via upload",
      description: "Placeholder for commit message when uploading files",
    },
    "ledgerEditor.chooseYourFiles": {
      message: "Escolher arquivos",
      description: "Button label to choose files for upload",
    },
    "ledgerEditor.commitMessage": {
      message: "Comentário de upload (opcional)",
      description: "Label for upload comment field when uploading files",
    },
    "ledgerEditor.dragFilesHere": {
      message: "Arraste arquivos aqui para adicioná-los ao seu repositório",
      description: "Instruction text in drag and drop upload area",
    },
    "ledgerEditor.exceedsFileSizeLimit": {
      message: "Excede o limite de 1MB",
      description: "Warning message when file size exceeds the maximum limit",
    },
    "ledgerEditor.removeOversizedFiles": {
      message: "Remova os arquivos maiores que 1 MB para enviar",
      description:
        "Explains why upload is disabled while oversized files are selected",
    },
    "ledgerEditor.fileAlreadyExists": {
      message: "Já existe nesta pasta",
      description:
        "Shown on a staged upload whose name already exists in the target folder",
    },
    "ledgerEditor.removeExistingFiles": {
      message: "Remova os arquivos que já existem nesta pasta para enviar",
      description:
        "Explains why upload is disabled while staged files already exist in the folder",
    },
    "ledgerEditor.uploadStoppedAt": {
      message: "{fileName} não foi enviado: {reason}",
      description:
        "Upload error naming the file that failed; {reason} is the localized cause",
    },
    "ledgerEditor.uploadedBeforeFailure": {
      message: "Enviados e removidos da lista: {files}",
      description:
        "After a failed upload, lists the files that were uploaded and removed from the staged list",
    },
    "ledgerEditor.maximumFileSize": {
      message: "Tamanho máximo do arquivo: 1MB",
      description: "Maximum file size limit text in upload area",
    },
    "ledgerEditor.or": {
      message: "ou",
      description:
        "Conjunction word between drag and drop and file picker options",
    },
    "ledgerEditor.removeSelectedFile": {
      message: "Remover {fileName}",
      description:
        "Aria label for removing a staged upload file; {fileName} is the file name",
    },
    "ledgerEditor.selectedFiles": {
      message: "Arquivos selecionados ({count})",
      description:
        "Label for selected files list (contains {count} placeholder)",
    },
    "ledgerEditor.uploading": {
      message: "Enviando...",
      description: "Message shown during file upload",
    },
  };

export default ptUploadFiles;
