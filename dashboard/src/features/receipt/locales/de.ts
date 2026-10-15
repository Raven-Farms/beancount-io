export interface TranslationEntry {
  message: string;
  description: string;
}

const deReceipt: Record<string, TranslationEntry> = {
  // Page
  "receipt.page.title": {
    message: "Beleg hochladen",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Laden Sie ein Belegbild oder PDF hoch, um eine Buchung in Ihrem Hauptbuch zu erfassen",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Beleg wird mit KI analysiert...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Dies kann bis zu 30 Sekunden dauern.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Etwas ist schiefgelaufen",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Erneut versuchen",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "Die Datei ist zu groß. Die maximale Größe beträgt 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Nicht unterstützter Dateityp. Bitte laden Sie eine PDF-, PNG-, JPG-, JPEG- oder WebP-Datei hoch.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Wird hochgeladen...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Andere Datei wählen",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Beleg hierher ziehen und ablegen",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Unterstützt PDF, PNG, JPG, JPEG, WebP — max. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Datei wählen",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "Datum ist erforderlich",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "Zahlungsempfänger ist erforderlich",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "Beschreibung ist erforderlich",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "Betrag muss eine positive Zahl sein",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "Währung ist erforderlich",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "Aufwandskonto ist erforderlich",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "Zahlungskonto ist erforderlich",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "Dokumentenkonto ist erforderlich",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Belegdetails",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Datum",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Zahlungsempfänger",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Händlername",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Beschreibung",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Buchungsbeschreibung",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Betrag",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Währung",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Konten",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Aufwandskonto",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Aufwandskonto auswählen",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Zahlungskonto",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Zahlungskonto auswählen",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Dokumentenkonto",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Dokumentenkonto auswählen",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Vorschau",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Anderen Beleg hochladen",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Buchung erfassen",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Buchung erfasst",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Ihr Beleg wurde in Ihrem Hauptbuch gespeichert.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Zahlungsempfänger",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Datum",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Betrag",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Aufwand",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Zahlung",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Journal anzeigen",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Weiteren Beleg hochladen",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "Beleg konnte nicht analysiert werden",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "Belegbuchung konnte nicht erfasst werden",
    description: "Error message when recording the transaction fails",
  },
};

export default deReceipt;
