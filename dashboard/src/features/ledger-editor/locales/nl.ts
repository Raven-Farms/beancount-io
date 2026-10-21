import nlDirectoryBrowse from "../directory-browse/locales/nl";
import nlFileEditor from "../file-editor/locales/nl";
import nlCreateFile from "../create-file/locales/nl";
import nlUploadFiles from "../upload-files/locales/nl";

const nlLedgerEditor: Record<string, { message: string; description: string }> =
  {
    "ledgerEditor.createFile": {
      message: "Bestand aanmaken",
      description: "Button label to create file",
    },
    "ledgerEditor.files": {
      message: "Bestanden",
      description: "Ledger files management",
    },
    "ledgerEditor.uploadFiles": {
      message: "Bestanden uploaden",
      description: "Tooltip for upload files button",
    },
  };

export default {
  ...nlDirectoryBrowse,
  ...nlFileEditor,
  ...nlCreateFile,
  ...nlUploadFiles,
  ...nlLedgerEditor,
  "ledgerEditor.gitClone": {
    message: "Git-kloon",
    description: "Button for opening Git clone options",
  },
  "ledgerEditor.failedToLoadDirectory": {
    message: "Kan de mapinhoud niet laden",
    description: "Error shown when a ledger directory cannot load",
  },
  "ledgerEditor.fileContentEmpty": {
    message: "Bestandsinhoud is leeg",
    description: "Empty state for a file without content",
  },
  "ledgerEditor.unableToDisplayImage": {
    message: "Kan de afbeeldingsinhoud niet weergeven",
    description: "Error shown when image content cannot be displayed",
  },
  "ledgerEditor.unsupportedPreviewWithType": {
    message:
      "Dit bestandstype ({type}) wordt niet ondersteund voor voorbeeldweergave",
    description: "Unsupported preview message including the file type",
  },
  "ledgerEditor.unsupportedPreview": {
    message: "Dit bestandstype wordt niet ondersteund voor voorbeeldweergave",
    description: "Unsupported preview message without a file type",
  },
  "ledgerEditor.notUtf8Text": {
    message:
      "Dit bestand is geen UTF-8-tekst en kan hier niet worden weergegeven of bewerkt zonder de bytes te wijzigen. Download het om het elders te openen.",
    description:
      "Shown instead of the editor for a text file whose bytes are not valid UTF-8",
  },
  "ledgerEditor.createFileCommit": {
    message: "Bestand aanmaken {path}",
    description: "Generated commit message for creating a file",
  },
  "ledgerEditor.updateFileCommit": {
    message: "Bestand bijwerken {path}",
    description: "Generated commit message for updating a file",
  },
  "ledgerEditor.deleteFileCommit": {
    message: "Bestand verwijderen {path}",
    description: "Generated commit message for deleting a file",
  },
};
