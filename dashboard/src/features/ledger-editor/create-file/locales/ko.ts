const koCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "파일 이름 입력...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: ". 또는 .. 세그먼트 없는 유효한 파일 경로를 입력하세요",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "빈 폴더 이름(// 또는 끝의 /)을 제거하세요",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: ".git 안의 파일은 편집할 수 없습니다",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "같은 이름의 파일이 이미 있습니다",
    description: "Validation error when create-file name collides",
  },
};

export default koCreateFile;
