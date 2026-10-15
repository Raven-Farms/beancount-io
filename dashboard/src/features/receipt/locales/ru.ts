export interface TranslationEntry {
  message: string;
  description: string;
}

const ruReceipt: Record<string, TranslationEntry> = {
  // Page
  "receipt.page.title": {
    message: "Загрузить чек",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Загрузите изображение или PDF чека, чтобы записать транзакцию в свою книгу",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Анализ чека с помощью ИИ...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Это может занять до 30 секунд.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Что-то пошло не так",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Повторить",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "Файл слишком большой. Максимальный размер — 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Неподдерживаемый тип файла. Загрузите PDF, PNG, JPG, JPEG или WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Загрузка...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Выбрать другой файл",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Перетащите чек сюда",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Поддерживаются PDF, PNG, JPG, JPEG, WebP — макс. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Выбрать файл",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "Укажите дату",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "Укажите получателя платежа",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "Укажите описание",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "Сумма должна быть положительным числом",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "Укажите валюту",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "Укажите счёт расходов",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "Укажите платёжный счёт",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "Укажите счёт документов",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Данные чека",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Дата",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Получатель платежа",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Название продавца",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Описание",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Описание транзакции",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Сумма",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Валюта",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Счета",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Счёт расходов",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Выберите счёт расходов",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Платёжный счёт",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Выберите платёжный счёт",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Счёт документов",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Выберите счёт документов",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Предпросмотр",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Загрузить другой чек",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Записать транзакцию",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Транзакция записана",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Ваш чек сохранён в книге.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Получатель платежа",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Дата",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Сумма",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Расход",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Оплата",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Открыть журнал",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Загрузить ещё один чек",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "Не удалось распознать чек",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "Не удалось записать транзакцию по чеку",
    description: "Error message when recording the transaction fails",
  },
};

export default ruReceipt;
