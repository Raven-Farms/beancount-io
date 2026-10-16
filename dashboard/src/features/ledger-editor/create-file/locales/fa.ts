const faCreateFile: Record<string, { message: string; description: string }> = {
  "ledgerEditor.nameYourFile": {
    message: "نام فایل را وارد کنید...",
    description: "Placeholder for file name input",
  },
  "ledgerEditor.invalidFilePath": {
    message: "یک مسیر فایل معتبر بدون بخش\u200cهای . یا .. وارد کنید",
    description: "Validation error for unsafe create-file paths",
  },
  "ledgerEditor.emptyFilePathSegment": {
    message: "نام خالی پوشه را حذف کنید (// یا / در انتها)",
    description: "Validation error for empty folder names in create-file paths",
  },
  "ledgerEditor.gitFilePathNotAllowed": {
    message: "فایل‌های داخل .git قابل ویرایش نیستند",
    description: "Validation error for reserved .git path segments",
  },
  "ledgerEditor.fileAlreadyExists": {
    message: "فایلی با این نام از قبل وجود دارد",
    description: "Validation error when create-file name collides",
  },
};

export default faCreateFile;
