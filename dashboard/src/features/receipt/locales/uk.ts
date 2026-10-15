export interface TranslationEntry {
  message: string;
  description: string;
}

const ukReceipt: Record<string, TranslationEntry> = {
  "receipt.access.title": {
    message: "Завантаження чеків недоступне",
    description: "Title when the receipt upload cannot be used",
  },
  "receipt.access.signedOut": {
    message: "Увійдіть, щоб завантажувати чеки до цієї книги.",
    description: "Explanation when a signed-out visitor opens receipt upload",
  },
  "receipt.access.readOnly": {
    message:
      "Ця книга доступна вам лише для читання. Щоб провести чек, потрібен доступ на запис. Ви й надалі можете переглядати її журнал, файли та запити.",
    description: "Explanation when the user cannot write to the ledger",
  },
  "receipt.access.unresolved": {
    message:
      "Не вдалося підтвердити доступ на запис. Завантаження чеків недоступне, доки права доступу до книги не буде визначено.",
    description: "Explanation when ledger write permissions are unavailable",
  },
  // Page
  "receipt.page.title": {
    message: "Завантажити чек",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Завантажте зображення або PDF чека, щоб записати транзакцію у свою книгу",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Аналіз чека за допомогою ШІ...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Це може зайняти до 30 секунд.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Щось пішло не так",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Спробувати ще раз",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "Файл завеликий. Максимальний розмір — 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Непідтримуваний тип файлу. Завантажте PDF, PNG, JPG, JPEG або WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Завантаження...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Вибрати інший файл",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Перетягніть чек сюди",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Підтримуються PDF, PNG, JPG, JPEG, WebP — макс. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Вибрати файл",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "Вкажіть дату",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "Вкажіть отримувача",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "Вкажіть опис",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "Сума має бути додатним числом",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "Вкажіть валюту",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "Вкажіть рахунок витрат",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "Вкажіть платіжний рахунок",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "Вкажіть рахунок документів",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Дані чека",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Дата",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Отримувач",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Назва продавця",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Опис",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Опис транзакції",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Сума",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Валюта",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Рахунки",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Рахунок витрат",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Виберіть рахунок витрат",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Платіжний рахунок",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Виберіть платіжний рахунок",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Рахунок документів",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Виберіть рахунок документів",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Попередній перегляд",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Завантажити інший чек",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Записати транзакцію",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Транзакцію записано",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Ваш чек збережено у книзі.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Отримувач",
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
    message: "Витрата",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Оплата",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Переглянути журнал",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Завантажити ще один чек",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "Не вдалося розпізнати чек",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "Не вдалося записати транзакцію за чеком",
    description: "Error message when recording the transaction fails",
  },
};

export default ukReceipt;
