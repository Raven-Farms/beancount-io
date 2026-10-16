const jaCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "ファイル名を入力...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: ". や .. を含まない有効なファイルパスを入力してください",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "空のフォルダー名（// または末尾の /）を削除してください",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: ".git 内のファイルは編集できません",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "同じ名前のファイルが既に存在します",
    description: "Validation error when create-file name collides",
  },
};

export default jaCreateFile;
