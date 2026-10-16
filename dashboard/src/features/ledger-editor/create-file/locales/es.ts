const esCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "Nombre your file...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "Introduce una ruta de archivo válida sin segmentos . o ..",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "Elimina el nombre de carpeta vacío (// o una / al final)",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "Los archivos dentro de .git no se pueden editar",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "Ya existe un archivo con este nombre",
    description: "Validation error when create-file name collides",
  },
};

export default esCreateFile;
