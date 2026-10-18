const jaUploadFiles: Record<string, { message: string; description: string }> =
  {
    "ledgerEditor.addFilesViaUpload": {
      message: "アップロードでファイルを追加",
      description: "Placeholder for commit message when uploading files",
    },
    "ledgerEditor.chooseYourFiles": {
      message: "ファイルを選択",
      description: "Button label to choose files for upload",
    },
    "ledgerEditor.commitMessage": {
      message: "アップロードコメント（任意）",
      description: "Label for upload comment field when uploading files",
    },
    "ledgerEditor.dragFilesHere": {
      message: "ファイルをここにドラッグしてリポジトリに追加",
      description: "Instruction text in drag and drop upload area",
    },
    "ledgerEditor.exceedsFileSizeLimit": {
      message: "1MBの制限を超えています",
      description: "Warning message when file size exceeds the maximum limit",
    },
    "ledgerEditor.removeOversizedFiles": {
      message: "アップロードするには 1 MB を超えるファイルを削除してください",
      description:
        "Explains why upload is disabled while oversized files are selected",
    },
    "ledgerEditor.fileAlreadyExists": {
      message: "このフォルダーに既に存在します",
      description:
        "Shown on a staged upload whose name already exists in the target folder",
    },
    "ledgerEditor.removeExistingFiles": {
      message:
        "アップロードするには、このフォルダーに既に存在するファイルを外してください",
      description:
        "Explains why upload is disabled while staged files already exist in the folder",
    },
    "ledgerEditor.uploadStoppedAt": {
      message: "{fileName} はアップロードされませんでした：{reason}",
      description:
        "Upload error naming the file that failed; {reason} is the localized cause",
    },
    "ledgerEditor.uploadedBeforeFailure": {
      message: "アップロード済みでリストから外したファイル：{files}",
      description:
        "After a failed upload, lists the files that were uploaded and removed from the staged list",
    },
    "ledgerEditor.maximumFileSize": {
      message: "最大ファイルサイズ: 1MB",
      description: "Maximum file size limit text in upload area",
    },
    "ledgerEditor.or": {
      message: "または",
      description:
        "Conjunction word between drag and drop and file picker options",
    },
    "ledgerEditor.removeSelectedFile": {
      message: "{fileName}を削除",
      description:
        "Aria label for removing a staged upload file; {fileName} is the file name",
    },
    "ledgerEditor.selectedFiles": {
      message: "選択したファイル（{count}）",
      description:
        "Label for selected files list (contains {count} placeholder)",
    },
    "ledgerEditor.uploading": {
      message: "アップロード中...",
      description: "Message shown during file upload",
    },
  };

export default jaUploadFiles;
