const ptCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "Nomeie seu arquivo...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "Digite um caminho de arquivo válido sem segmentos . ou ..",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "Remova o nome de pasta vazio (// ou uma / no final)",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "Os arquivos dentro de .git não podem ser editados",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "Já existe um arquivo com este nome",
    description: "Validation error when create-file name collides",
  },
};

export default ptCreateFile;
