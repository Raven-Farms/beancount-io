const deCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "Benennen Sie Ihre Datei...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "Geben Sie einen gültigen Dateipfad ohne . oder .. Segmente ein",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message:
      "Entfernen Sie den leeren Ordnernamen (// oder ein abschließendes /)",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "Dateien innerhalb von .git können nicht bearbeitet werden",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "Eine Datei mit diesem Namen existiert bereits",
    description: "Validation error when create-file name collides",
  },
};

export default deCreateFile;
