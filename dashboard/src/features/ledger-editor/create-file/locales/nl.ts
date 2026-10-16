const nlCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "Naam your file...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "Voer een geldig bestandspad in zonder . of .. segmenten",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "Verwijder de lege mapnaam (// of een / aan het einde)",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "Bestanden in .git kunnen niet worden bewerkt",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "Er bestaat al een bestand met deze naam",
    description: "Validation error when create-file name collides",
  },
};

export default nlCreateFile;
