const ruCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "Имя вашего файла...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "Введите допустимый путь без сегментов . или ..",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "Удалите пустое имя папки (// или / в конце)",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "Файлы внутри .git нельзя редактировать",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "Файл с таким именем уже существует",
    description: "Validation error when create-file name collides",
  },
};

export default ruCreateFile;
