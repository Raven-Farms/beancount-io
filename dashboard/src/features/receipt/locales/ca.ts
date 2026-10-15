export interface TranslationEntry {
  message: string;
  description: string;
}

const caReceipt: Record<string, TranslationEntry> = {
  "receipt.access.title": {
    message: "La pujada de rebuts no està disponible",
    description: "Title when the receipt upload cannot be used",
  },
  "receipt.access.signedOut": {
    message: "Inicia la sessió per pujar rebuts a aquest llibre comptable.",
    description: "Explanation when a signed-out visitor opens receipt upload",
  },
  "receipt.access.readOnly": {
    message:
      "Aquest llibre comptable és només de lectura per a tu. Registrar un rebut requereix accés d’escriptura. Encara pots explorar-ne el diari, els fitxers i les consultes.",
    description: "Explanation when the user cannot write to the ledger",
  },
  "receipt.access.unresolved": {
    message:
      "No s’ha pogut confirmar l’accés d’escriptura. La pujada de rebuts no estarà disponible fins que es resolguin els teus permisos del llibre comptable.",
    description: "Explanation when ledger write permissions are unavailable",
  },
  // Page
  "receipt.page.title": {
    message: "Pujar rebut",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Puja una imatge o un PDF d'un rebut per registrar una transacció al teu llibre",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Analitzant el rebut amb IA...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Això pot trigar fins a 30 segons.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Alguna cosa ha anat malament",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Torna-ho a provar",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "El fitxer és massa gran. La mida màxima és de 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Tipus de fitxer no compatible. Puja un PDF, PNG, JPG, JPEG o WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Pujant...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Tria un altre fitxer",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Arrossega i deixa anar el rebut aquí",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Admet PDF, PNG, JPG, JPEG, WebP — màx. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Tria un fitxer",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "La data és obligatòria",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "El beneficiari és obligatori",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "La descripció és obligatòria",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "L'import ha de ser un nombre positiu",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "La moneda és obligatòria",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "El compte de despeses és obligatori",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "El compte de pagament és obligatori",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "El compte de documents és obligatori",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Detalls del rebut",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Data",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Beneficiari",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Nom del comerç",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Descripció",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Descripció de la transacció",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Import",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Moneda",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Comptes",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Compte de despeses",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Selecciona el compte de despeses",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Compte de pagament",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Selecciona el compte de pagament",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Compte de documents",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Selecciona el compte de documents",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Previsualització",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Puja un altre rebut",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Registra la transacció",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Transacció registrada",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "El teu rebut s'ha desat al teu llibre.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Beneficiari",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Data",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Import",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Despesa",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Pagament",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Veure el diari",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Puja un altre rebut",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "No s'ha pogut analitzar el rebut",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "No s'ha pogut registrar la transacció del rebut",
    description: "Error message when recording the transaction fails",
  },
};

export default caReceipt;
