export interface TranslationEntry {
  message: string;
  description: string;
}

const ptReceipt: Record<string, TranslationEntry> = {
  "receipt.access.title": {
    message: "Envio de recibos indisponível",
    description: "Title when the receipt upload cannot be used",
  },
  "receipt.access.signedOut": {
    message: "Entre para enviar recibos para este livro-razão.",
    description: "Explanation when a signed-out visitor opens receipt upload",
  },
  "receipt.access.readOnly": {
    message:
      "Este livro-razão é somente leitura para você. Registrar um recibo exige acesso de escrita. Você ainda pode explorar o diário, os arquivos e as consultas.",
    description: "Explanation when the user cannot write to the ledger",
  },
  "receipt.access.unresolved": {
    message:
      "Não foi possível confirmar o acesso de escrita. O envio de recibos fica indisponível até que suas permissões do livro-razão sejam resolvidas.",
    description: "Explanation when ledger write permissions are unavailable",
  },
  // Page
  "receipt.page.title": {
    message: "Carregar recibo",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Carregue uma imagem ou PDF de um recibo para registrar uma transação no seu livro",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Analisando o recibo com IA...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Isso pode levar até 30 segundos.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Algo deu errado",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Tentar novamente",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "O arquivo é muito grande. O tamanho máximo é 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Tipo de arquivo não suportado. Carregue um PDF, PNG, JPG, JPEG ou WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Carregando...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Escolher outro arquivo",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Arraste e solte seu recibo aqui",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Suporta PDF, PNG, JPG, JPEG, WebP — máx. 5MB",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Escolher arquivo",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "A data é obrigatória",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "O beneficiário é obrigatório",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "A descrição é obrigatória",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "O valor deve ser um número positivo",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "A moeda é obrigatória",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "A conta de despesa é obrigatória",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "A conta de pagamento é obrigatória",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "A conta de documentos é obrigatória",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Detalhes do recibo",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Data",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Beneficiário",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Nome do estabelecimento",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Descrição",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Descrição da transação",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Valor",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Moeda",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Contas",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Conta de despesa",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Selecione a conta de despesa",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Conta de pagamento",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Selecione a conta de pagamento",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Conta de documentos",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Selecione a conta de documentos",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Pré-visualização",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Carregar outro recibo",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Registrar transação",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Transação registrada",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Seu recibo foi salvo no seu livro.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Beneficiário",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Data",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Valor",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Despesa",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Pagamento",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Ver diário",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Carregar outro recibo",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "Falha ao analisar o recibo",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "Falha ao registrar a transação do recibo",
    description: "Error message when recording the transaction fails",
  },
};

export default ptReceipt;
