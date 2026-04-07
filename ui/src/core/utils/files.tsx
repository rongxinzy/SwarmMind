import {
  FileIcon,
  FileTextIcon,
  FileCodeIcon,
  FileImageIcon,
  FileJsonIcon,
  FileSpreadsheetIcon,
  type LucideIcon,
} from "lucide-react";

/**
 * Get file extension from filename
 */
export const getFileExt = (filename: string): string => {
  return filename.split(".").pop()?.toLowerCase() ?? "";
};

/**
 * File type mapping for display names
 */
export const FILE_TYPE_MAP: Record<string, string> = {
  json: "JSON",
  csv: "CSV",
  txt: "TXT",
  md: "Markdown",
  py: "Python",
  js: "JavaScript",
  ts: "TypeScript",
  tsx: "TSX",
  jsx: "JSX",
  html: "HTML",
  css: "CSS",
  xml: "XML",
  yaml: "YAML",
  yml: "YAML",
  pdf: "PDF",
  png: "PNG",
  jpg: "JPG",
  jpeg: "JPEG",
  gif: "GIF",
  svg: "SVG",
  webp: "WebP",
  zip: "ZIP",
  tar: "TAR",
  gz: "GZ",
  sql: "SQL",
  sh: "Shell",
  bash: "Bash",
  zsh: "Zsh",
  skill: "Skill",
};

/**
 * File icon mapping
 */
export const FILE_ICON_MAP: Record<string, LucideIcon> = {
  js: FileCodeIcon,
  ts: FileCodeIcon,
  tsx: FileCodeIcon,
  jsx: FileCodeIcon,
  html: FileCodeIcon,
  css: FileCodeIcon,
  py: FileCodeIcon,
  json: FileJsonIcon,
  csv: FileSpreadsheetIcon,
  md: FileTextIcon,
  txt: FileTextIcon,
  pdf: FileIcon,
  png: FileImageIcon,
  jpg: FileImageIcon,
  jpeg: FileImageIcon,
  gif: FileImageIcon,
  svg: FileImageIcon,
  webp: FileImageIcon,
};

/**
 * Image file extensions
 */
export const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico"];

/**
 * Get display name for file type
 */
export function getFileTypeDisplayName(filename: string): string {
  const ext = getFileExt(filename);
  return FILE_TYPE_MAP[ext] ?? (ext ? ext.toUpperCase() : "FILE");
}

/**
 * Check if file is an image
 */
export function isImageFile(filename: string): boolean {
  return IMAGE_EXTENSIONS.includes(getFileExt(filename));
}

/**
 * Get icon for file
 */
export function getFileIcon(filename: string, className?: string): React.ReactNode {
  const ext = getFileExt(filename);
  const Icon = FILE_ICON_MAP[ext] || FileIcon;
  return <Icon className={className} />;
}

/**
 * Get filename without path
 */
export function getFileName(filepath: string): string {
  return filepath.split("/").pop() ?? filepath;
}

/**
 * Get file extension display name
 */
export function getFileExtensionDisplayName(filepath: string): string {
  const filename = getFileName(filepath);
  return getFileTypeDisplayName(filename);
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Check if file is a code file
 */
export function isCodeFile(filename: string): boolean {
  const codeExtensions = [
    "js", "ts", "jsx", "tsx", "py", "java", "cpp", "c", "h", "hpp",
    "go", "rs", "rb", "php", "swift", "kt", "scala", "r", "m", "mm",
    "html", "css", "scss", "sass", "less", "json", "xml", "yaml", "yml",
    "sql", "sh", "bash", "zsh", "fish", "ps1", "bat", "cmd"
  ];
  return codeExtensions.includes(getFileExt(filename));
}

/**
 * Get language for syntax highlighting from filename
 */
export function getLanguageFromFilename(filename: string): string {
  const ext = getFileExt(filename);
  const langMap: Record<string, string> = {
    js: "javascript",
    ts: "typescript",
    jsx: "jsx",
    tsx: "tsx",
    py: "python",
    java: "java",
    cpp: "cpp",
    c: "c",
    h: "c",
    hpp: "cpp",
    go: "go",
    rs: "rust",
    rb: "ruby",
    php: "php",
    swift: "swift",
    kt: "kotlin",
    scala: "scala",
    r: "r",
    html: "html",
    css: "css",
    scss: "scss",
    sass: "sass",
    json: "json",
    xml: "xml",
    yaml: "yaml",
    yml: "yaml",
    sql: "sql",
    sh: "bash",
    bash: "bash",
    zsh: "bash",
    md: "markdown",
    txt: "text",
  };
  return langMap[ext] || "text";
}
