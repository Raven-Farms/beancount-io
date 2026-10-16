const frCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "Nommez votre fichier...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "Saisissez un chemin de fichier valide sans segments . ou ..",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "Supprimez le nom de dossier vide (// ou / à la fin)",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "Les fichiers dans .git ne peuvent pas être modifiés",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "Un fichier portant ce nom existe déjà",
    description: "Validation error when create-file name collides",
  },
};

export default frCreateFile;
