export interface TranslationEntry {
  message: string;
  description: string;
}

const esReceipt: Record<string, TranslationEntry> = {
  // Page
  "receipt.page.title": {
    message: "Subir recibo",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Sube una imagen o un PDF de un recibo para registrar una transacción en tu libro",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Analizando el recibo con IA...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Esto puede tardar hasta 30 segundos.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Algo salió mal",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Intentar de nuevo",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "El archivo es demasiado grande. El tamaño máximo es de 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Tipo de archivo no compatible. Sube un PDF, PNG, JPG, JPEG o WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Subiendo...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Elegir otro archivo",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Arrastra y suelta tu recibo aquí",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Admite PDF, PNG, JPG, JPEG, WebP — máx. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Elegir archivo",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "La fecha es obligatoria",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "El beneficiario es obligatorio",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "La descripción es obligatoria",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "El importe debe ser un número positivo",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "La moneda es obligatoria",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "La cuenta de gastos es obligatoria",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "La cuenta de pago es obligatoria",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "La cuenta de documentos es obligatoria",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Detalles del recibo",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Fecha",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Beneficiario",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Nombre del comercio",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Descripción",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Descripción de la transacción",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Importe",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Moneda",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Cuentas",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Cuenta de gastos",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Selecciona la cuenta de gastos",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Cuenta de pago",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Selecciona la cuenta de pago",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Cuenta de documentos",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Selecciona la cuenta de documentos",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Vista previa",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Subir otro recibo",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Registrar transacción",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Transacción registrada",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Tu recibo se ha guardado en tu libro.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Beneficiario",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Fecha",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Importe",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Gasto",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Pago",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Ver diario",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Subir otro recibo",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "No se pudo analizar el recibo",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "No se pudo registrar la transacción del recibo",
    description: "Error message when recording the transaction fails",
  },
};

export default esReceipt;
