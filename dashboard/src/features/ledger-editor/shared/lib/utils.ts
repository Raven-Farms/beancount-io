export const getParentPath = (filePath: string) => {
  return filePath.split("/").slice(0, -1).join("/");
};

/**
 * Format file size in bytes to human readable format
 */
export const formatFileSize = (bytes: number, decimals = 2) => {
  if (bytes === 0) return "0 B";

  // Handle negative numbers by using absolute value
  const absBytes = Math.abs(bytes);
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(absBytes) / Math.log(k));

  // Ensure i is within bounds of sizes array
  const sizeIndex = Math.min(i, sizes.length - 1);
  const formattedValue = parseFloat(
    (absBytes / Math.pow(k, sizeIndex)).toFixed(decimals),
  );

  return (bytes < 0 ? "-" : "") + formattedValue + " " + sizes[sizeIndex];
};

/**
 * Get file extension from filename (lowercase)
 * Returns empty string if file has no extension
 */
export const getFileExtension = (filename: string): string => {
  const parts = filename.split(".");
  // If there's only one part, there's no extension
  if (parts.length === 1) return "";
  return parts.pop()?.toLowerCase() || "";
};

/**
 * Extract filename from file path
 * @param filePath - The full file path
 * @returns The filename (last part of the path)
 */
export const getFilename = (filePath: string): string => {
  return filePath.split("/").pop() || "";
};

/**
 * Well-known text basenames (extensionless or dotfiles) that should be treated
 * as text even though they have no extension. Lowercased, leading dot stripped.
 * Inspired by GitHub Linguist well-known filenames.
 */
export const TEXT_BASENAMES = new Set<string>([
  "license",
  "licence",
  "copying",
  "copyright",
  "readme",
  "contributing",
  "code_of_conduct",
  "changelog",
  "history",
  "authors",
  "makefile",
  "gnumakefile",
  "dockerfile",
  "containerfile",
  "gemfile",
  "rakefile",
  "vagrantfile",
  "procfile",
  "gitignore",
  "gitattributes",
  "editorconfig",
  "env",
  "env.example",
]);

const getNormalizedBasename = (filename: string): string =>
  getFilename(filename).toLowerCase().replace(/^\./, "");

/**
 * Check if file is an image based on extension
 */
export const isImageFile = (filename: string): boolean => {
  const imageExtensions = ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"];
  return imageExtensions.includes(getFileExtension(filename));
};

/**
 * Check if file is a text file based on extension or well-known basename
 */
export const isTextFile = (filename: string): boolean => {
  const textExtensions = [
    "txt",
    "md",
    "json",
    "yaml",
    "yml",
    "xml",
    "html",
    "css",
    "js",
    "ts",
    "tsx",
    "jsx",
    "py",
    "java",
    "cpp",
    "c",
    "h",
    "sql",
    "sh",
    "bash",
    "beancount",
    "bean",
    "csv",
    "tsv",
    "ofx",
    "qfx",
    "qif",
    "toml",
    "ini",
    "cfg",
    "conf",
    "log",
  ];
  const ext = getFileExtension(filename);
  if (textExtensions.includes(ext)) return true;
  if (TEXT_BASENAMES.has(getNormalizedBasename(filename))) return true;
  return false;
};

/**
 * Check if file is a PDF based on extension
 */
export const isPDFFile = (filename: string): boolean => {
  return filename.toLowerCase().endsWith(".pdf");
};

/**
 * File type categories
 */
export type FileType = "image" | "pdf" | "text" | "unknown";

/**
 * Get file type category based on filename
 * @param filename - The name of the file
 * @returns The file type category
 */
export const getFileType = (filename: string): FileType => {
  if (isImageFile(filename)) {
    return "image";
  }
  if (isPDFFile(filename)) {
    return "pdf";
  }
  if (isTextFile(filename)) {
    return "text";
  }
  return "unknown";
};

const MAX_TEXT_PREVIEW_BYTES = 1024 * 1024;

const decodeBase64Bytes = (content: string) =>
  Uint8Array.from(atob(content), (character) => character.charCodeAt(0));

/** Unknown formats may be previewed only as bounded, valid UTF-8 text. */
export const isPreviewableTextContent = (
  content: string | null | undefined,
  size: number,
): boolean => {
  if (
    typeof content !== "string" ||
    !Number.isFinite(size) ||
    size < 0 ||
    size > MAX_TEXT_PREVIEW_BYTES
  ) {
    return false;
  }

  // Count without allocating a whitespace-stripped copy. Repository base64
  // may be line-wrapped; only encoded characters contribute to decoded size.
  const maxEncodedLength = Math.ceil(MAX_TEXT_PREVIEW_BYTES / 3) * 4;
  let encodedLength = 0;
  let padding = 0;
  for (let index = 0; index < content.length; index++) {
    const code = content.charCodeAt(index);
    if (
      code === 9 ||
      code === 10 ||
      code === 12 ||
      code === 13 ||
      code === 32
    ) {
      continue;
    }
    if (++encodedLength > maxEncodedLength) return false;
    padding = code === 61 ? padding + 1 : 0;
  }
  if (Math.floor((encodedLength * 3) / 4) - padding > MAX_TEXT_PREVIEW_BYTES) {
    return false;
  }

  try {
    const bytes = decodeBase64Bytes(content);
    if (bytes.length > MAX_TEXT_PREVIEW_BYTES || bytes.includes(0))
      return false;
    new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return true;
  } catch {
    return false;
  }
};

/**
 * Get Monaco editor language from filename
 * Checks well-known basenames before extension map so extensionless files
 * like Makefile/Dockerfile get proper highlighting.
 */
export const getFileLanguage = (filename: string): string => {
  const base = getNormalizedBasename(filename);
  const basenameLanguageMap: Record<string, string> = {
    makefile: "makefile",
    gnumakefile: "makefile",
    dockerfile: "dockerfile",
    containerfile: "dockerfile",
    readme: "markdown",
    // licenselike and other text basenames fall through to plaintext
  };
  if (basenameLanguageMap[base]) return basenameLanguageMap[base];

  const ext = getFileExtension(filename);
  const languageMap: Record<string, string> = {
    js: "javascript",
    jsx: "javascript",
    ts: "typescript",
    tsx: "typescript",
    json: "json",
    html: "html",
    css: "css",
    py: "python",
    md: "markdown",
    sql: "sql",
    yaml: "yaml",
    yml: "yaml",
    xml: "xml",
    ofx: "xml",
    qfx: "xml",
    ini: "ini",
    cfg: "ini",
    conf: "ini",
    sh: "shell",
    bash: "shell",
    bean: "beancount",
    beancount: "beancount",
  };
  return languageMap[ext] || "plaintext";
};

/**
 * Get MIME type from file extension or well-known basename
 */
export const getMimeTypeFromExtension = (filename: string): string => {
  // Well-known extensionless text files should be treated as text/plain
  if (TEXT_BASENAMES.has(getNormalizedBasename(filename))) return "text/plain";

  const ext = getFileExtension(filename);
  switch (ext) {
    case "txt":
    case "md":
    case "beancount":
    case "bean":
    case "json":
    case "yaml":
    case "yml":
    case "xml":
    case "html":
    case "css":
    case "js":
    case "ts":
    case "tsx":
    case "jsx":
    case "py":
    case "java":
    case "cpp":
    case "c":
    case "h":
    case "sql":
    case "sh":
    case "bash":
      return "text/plain";
    case "svg":
      return "image/svg+xml";
    case "png":
      return "image/png";
    case "jpg":
    case "jpeg":
      return "image/jpeg";
    case "gif":
      return "image/gif";
    case "webp":
      return "image/webp";
    default:
      return "application/octet-stream";
  }
};

/**
 * MIME for the download Blob. Extensionless text basenames (Makefile,
 * LICENSE, …) stay text/plain for preview/editor classification, but Chrome
 * appends .txt when a text/plain download has no extension — use octet-stream
 * so the suggested filename keeps the repository basename.
 */
export const getDownloadMimeType = (filename: string): string => {
  if (TEXT_BASENAMES.has(getNormalizedBasename(filename))) {
    return "application/octet-stream";
  }
  return getMimeTypeFromExtension(filename);
};

/**
 * Download a file from base64 content
 * @param filename - The name of the file to download
 * @param base64Content - The base64 encoded file content
 */
export const downloadFile = (filename: string, base64Content: string): void => {
  if (!base64Content) return;

  // Handle image files
  if (isImageFile(filename)) {
    const mimeType = getMimeTypeFromExtension(filename);
    const href = `data:${mimeType};base64,${base64Content}`;
    const link = document.createElement("a");
    link.href = href;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    return;
  }

  // Handle text files
  if (isTextFile(filename)) {
    const bytes = decodeBase64Bytes(base64Content);
    const mime = `${getDownloadMimeType(filename)};charset=utf-8`;
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    return;
  }

  // Handle other files as binary
  const href = `data:application/octet-stream;base64,${base64Content}`;
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
};
