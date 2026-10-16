const caCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "Nom del fitxer...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "Introduïu un camí de fitxer vàlid sense segments . o ..",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "Elimineu el nom de carpeta buit (// o una / final)",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "Els fitxers dins de .git no es poden editar",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "Ja existeix un fitxer amb aquest nom",
    description: "Validation error when create-file name collides",
  },
};

export default caCreateFile;
