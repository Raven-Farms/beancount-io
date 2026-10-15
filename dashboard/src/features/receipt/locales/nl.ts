export interface TranslationEntry {
  message: string;
  description: string;
}

const nlReceipt: Record<string, TranslationEntry> = {
  "receipt.access.title": {
    message: "Bon uploaden niet beschikbaar",
    description: "Title when the receipt upload cannot be used",
  },
  "receipt.access.signedOut": {
    message: "Meld u aan om bonnen naar dit grootboek te uploaden.",
    description: "Explanation when a signed-out visitor opens receipt upload",
  },
  "receipt.access.readOnly": {
    message:
      "Dit grootboek is voor u alleen-lezen. Voor het boeken van een bon is schrijftoegang nodig. U kunt het journaal, de bestanden en de query's nog steeds bekijken.",
    description: "Explanation when the user cannot write to the ledger",
  },
  "receipt.access.unresolved": {
    message:
      "Schrijftoegang kon niet worden bevestigd. Bonnen uploaden is niet beschikbaar totdat uw grootboekrechten zijn vastgesteld.",
    description: "Explanation when ledger write permissions are unavailable",
  },
  // Page
  "receipt.page.title": {
    message: "Bon uploaden",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Upload een afbeelding of PDF van een bon om een transactie in je grootboek vast te leggen",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Bon wordt geanalyseerd met AI...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Dit kan tot 30 seconden duren.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Er is iets misgegaan",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Opnieuw proberen",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "Het bestand is te groot. De maximale grootte is 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Niet-ondersteund bestandstype. Upload een PDF, PNG, JPG, JPEG of WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Bezig met uploaden...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Ander bestand kiezen",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Sleep je bon hierheen",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Ondersteunt PDF, PNG, JPG, JPEG, WebP — max. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Bestand kiezen",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "Datum is verplicht",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "Begunstigde is verplicht",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "Omschrijving is verplicht",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "Bedrag moet een positief getal zijn",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "Valuta is verplicht",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "Kostenrekening is verplicht",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "Betaalrekening is verplicht",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "Documentrekening is verplicht",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Bongegevens",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Datum",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Begunstigde",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Naam van handelaar",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Omschrijving",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Omschrijving van transactie",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Bedrag",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Valuta",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Rekeningen",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Kostenrekening",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Kostenrekening selecteren",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Betaalrekening",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Betaalrekening selecteren",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Documentrekening",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Documentrekening selecteren",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Voorbeeld",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Andere bon uploaden",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Transactie vastleggen",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Transactie vastgelegd",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Je bon is opgeslagen in je grootboek.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Begunstigde",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Datum",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Bedrag",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Kosten",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Betaling",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Dagboek bekijken",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Nog een bon uploaden",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "Bon kon niet worden geanalyseerd",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "Transactie van bon kon niet worden vastgelegd",
    description: "Error message when recording the transaction fails",
  },
};

export default nlReceipt;
