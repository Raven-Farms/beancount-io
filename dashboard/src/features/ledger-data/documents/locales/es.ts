export interface TranslationEntry {
  message: string;
  description: string;
}

const esDocuments: Record<string, TranslationEntry> = {
  "page.documents.documents": {
    message: "Documentos",
    description: "Documents attached to ledger entries",
  },
  "page.documents.filename": {
    message: "Nombre de archivo",
    description: "Table column header for filename",
  },
  "page.documents.links": {
    message: "Enlaces",
    description: "Table column header for links",
  },
  "page.documents.meta": {
    message: "Metadatos",
    description: "Table column header for metadata",
  },
  "page.documents.noDocumentsFound": {
    message: "No se encontraron documentos en este libro mayor.",
    description: "Empty state message for no documents",
  },
  "page.documents.noDocumentsFoundDescription": {
    message:
      "Agregue documentos a sus archivos de libro mayor para verlos aquí.",
    description: "Empty state description for no documents",
  },
  "page.documents.tags": {
    message: "Etiquetas",
    description: "Table column header for tags",
  },
};

export default esDocuments;
