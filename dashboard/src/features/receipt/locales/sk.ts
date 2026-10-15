export interface TranslationEntry {
  message: string;
  description: string;
}

const skReceipt: Record<string, TranslationEntry> = {
  // Page
  "receipt.page.title": {
    message: "Nahrať bloček",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Nahrajte obrázok alebo PDF bločku a zaznamenajte transakciu do svojej knihy",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Bloček sa analyzuje pomocou AI...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Môže to trvať až 30 sekúnd.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Niečo sa pokazilo",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Skúsiť znova",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "Súbor je príliš veľký. Maximálna veľkosť je 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Nepodporovaný typ súboru. Nahrajte PDF, PNG, JPG, JPEG alebo WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Nahráva sa...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Vybrať iný súbor",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Presuňte bloček sem",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Podporuje PDF, PNG, JPG, JPEG, WebP — max. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Vybrať súbor",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "Dátum je povinný",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "Príjemca je povinný",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "Popis je povinný",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "Suma musí byť kladné číslo",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "Mena je povinná",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "Nákladový účet je povinný",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "Platobný účet je povinný",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "Účet dokumentov je povinný",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Podrobnosti bločku",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Dátum",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Príjemca",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Názov obchodníka",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Popis",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Popis transakcie",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Suma",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Mena",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Účty",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Nákladový účet",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Vyberte nákladový účet",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Platobný účet",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Vyberte platobný účet",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Účet dokumentov",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Vyberte účet dokumentov",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Náhľad",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Nahrať iný bloček",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Zaznamenať transakciu",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Transakcia zaznamenaná",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Váš bloček bol uložený do vašej knihy.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Príjemca",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Dátum",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Suma",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Náklad",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Platba",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Zobraziť denník",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Nahrať ďalší bloček",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "Bloček sa nepodarilo analyzovať",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "Transakciu z bločku sa nepodarilo zaznamenať",
    description: "Error message when recording the transaction fails",
  },
};

export default skReceipt;
