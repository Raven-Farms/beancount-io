const zhCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "命名你的文件...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "请输入有效的文件路径，不能包含 . 或 .. 段",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "请移除空文件夹名称（// 或末尾的 /）",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "无法编辑 .git 中的文件",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "已存在同名文件",
    description: "Validation error when create-file name collides",
  },
};

export default zhCreateFile;
