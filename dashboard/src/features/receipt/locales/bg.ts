export interface TranslationEntry {
  message: string;
  description: string;
}

const bgReceipt: Record<string, TranslationEntry> = {
  "receipt.access.title": {
    message: "Качването на касови бележки не е налично",
    description: "Title when the receipt upload cannot be used",
  },
  "receipt.access.signedOut": {
    message: "Влезте, за да качвате касови бележки в тази книга.",
    description: "Explanation when a signed-out visitor opens receipt upload",
  },
  "receipt.access.readOnly": {
    message:
      "Тази книга е само за четене за вас. За осчетоводяване на касова бележка е нужен достъп за запис. Все още можете да разглеждате нейния дневник, файлове и заявки.",
    description: "Explanation when the user cannot write to the ledger",
  },
  "receipt.access.unresolved": {
    message:
      "Достъпът за запис не можа да бъде потвърден. Качването на касови бележки не е налично, докато правата ви за книгата не бъдат изяснени.",
    description: "Explanation when ledger write permissions are unavailable",
  },
  // Page
  "receipt.page.title": {
    message: "Качи разписка",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Качете изображение или PDF на разписка, за да запишете транзакция в книгата си",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Анализиране на разписката с ИИ...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Това може да отнеме до 30 секунди.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Нещо се обърка",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Опитай отново",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "Файлът е твърде голям. Максималният размер е 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message: "Неподдържан тип файл. Моля, качете PDF, PNG, JPG, JPEG или WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Качване...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Избери друг файл",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Плъзнете и пуснете разписката си тук",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Поддържа PDF, PNG, JPG, JPEG, WebP — макс. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Избери файл",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "Датата е задължителна",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "Получателят е задължителен",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "Описанието е задължително",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "Сумата трябва да е положително число",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "Валутата е задължителна",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "Сметката за разходи е задължителна",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "Платежната сметка е задължителна",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "Сметката за документи е задължителна",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Данни за разписката",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Дата",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Получател",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Име на търговеца",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Описание",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Описание на транзакцията",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Сума",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Валута",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Сметки",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Сметка за разходи",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Изберете сметка за разходи",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Платежна сметка",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Изберете платежна сметка",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Сметка за документи",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Изберете сметка за документи",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Преглед",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Качи друга разписка",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Запиши транзакцията",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Транзакцията е записана",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Разписката ви е запазена в книгата.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Получател",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Дата",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Сума",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Разход",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Плащане",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Към дневника",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Качи още една разписка",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "Неуспешен анализ на разписката",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "Неуспешно записване на транзакцията от разписката",
    description: "Error message when recording the transaction fails",
  },
};

export default bgReceipt;
