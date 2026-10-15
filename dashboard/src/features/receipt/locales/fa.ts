export interface TranslationEntry {
  message: string;
  description: string;
}

const faReceipt: Record<string, TranslationEntry> = {
  "receipt.access.title": {
    message: "بارگذاری رسید در دسترس نیست",
    description: "Title when the receipt upload cannot be used",
  },
  "receipt.access.signedOut": {
    message: "برای بارگذاری رسید در این دفتر وارد حساب شوید.",
    description: "Explanation when a signed-out visitor opens receipt upload",
  },
  "receipt.access.readOnly": {
    message:
      "این دفتر برای شما فقط‌خواندنی است. ثبت رسید به دسترسی نوشتن نیاز دارد. همچنان می‌توانید دفتر روزنامه، فایل‌ها و پرس‌وجوهای آن را مرور کنید.",
    description: "Explanation when the user cannot write to the ledger",
  },
  "receipt.access.unresolved": {
    message:
      "دسترسی نوشتن تأیید نشد. تا زمانی که مجوزهای دفتر شما مشخص نشود، بارگذاری رسید در دسترس نیست.",
    description: "Explanation when ledger write permissions are unavailable",
  },
  // Page
  "receipt.page.title": {
    message: "آپلود رسید",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message: "تصویر یا PDF رسید را آپلود کنید تا تراکنشی در دفتر شما ثبت شود",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "در حال تحلیل رسید با هوش مصنوعی...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "این کار ممکن است تا 30 ثانیه طول بکشد.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "مشکلی پیش آمد",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "تلاش دوباره",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "فایل بیش از حد بزرگ است. حداکثر اندازه 5MB است.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "نوع فایل پشتیبانی نمی‌شود. لطفاً یک فایل PDF، PNG، JPG، JPEG یا WebP آپلود کنید.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "در حال آپلود...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "انتخاب فایل دیگر",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "رسید خود را اینجا بکشید و رها کنید",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "پشتیبانی از PDF، PNG، JPG، JPEG، WebP — حداکثر 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "انتخاب فایل",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "تاریخ الزامی است",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "دریافت‌کننده الزامی است",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "توضیحات الزامی است",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "مبلغ باید یک عدد مثبت باشد",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "ارز الزامی است",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "حساب هزینه الزامی است",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "حساب پرداخت الزامی است",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "حساب اسناد الزامی است",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "جزئیات رسید",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "تاریخ",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "دریافت‌کننده",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "نام فروشنده",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "توضیحات",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "توضیحات تراکنش",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "مبلغ",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "ارز",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "حساب‌ها",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "حساب هزینه",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "انتخاب حساب هزینه",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "حساب پرداخت",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "انتخاب حساب پرداخت",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "حساب اسناد",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "انتخاب حساب اسناد",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "پیش‌نمایش",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "آپلود رسید دیگر",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "ثبت تراکنش",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "تراکنش ثبت شد",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "رسید شما در دفترتان ذخیره شد.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "دریافت‌کننده",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "تاریخ",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "مبلغ",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "هزینه",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "پرداخت",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "مشاهده دفتر روزنامه",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "آپلود رسید دیگر",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "تحلیل رسید ناموفق بود",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "ثبت تراکنش رسید ناموفق بود",
    description: "Error message when recording the transaction fails",
  },
};

export default faReceipt;
