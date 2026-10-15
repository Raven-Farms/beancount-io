export interface TranslationEntry {
  message: string;
  description: string;
}

const frReceipt: Record<string, TranslationEntry> = {
  "receipt.access.title": {
    message: "Envoi de reçu indisponible",
    description: "Title when the receipt upload cannot be used",
  },
  "receipt.access.signedOut": {
    message: "Connectez-vous pour envoyer des reçus dans ce registre.",
    description: "Explanation when a signed-out visitor opens receipt upload",
  },
  "receipt.access.readOnly": {
    message:
      "Ce registre est en lecture seule pour vous. Enregistrer un reçu nécessite un accès en écriture. Vous pouvez toujours consulter son journal, ses fichiers et ses requêtes.",
    description: "Explanation when the user cannot write to the ledger",
  },
  "receipt.access.unresolved": {
    message:
      "L’accès en écriture n’a pas pu être confirmé. L’envoi de reçus est indisponible tant que vos autorisations sur le registre ne sont pas résolues.",
    description: "Explanation when ledger write permissions are unavailable",
  },
  // Page
  "receipt.page.title": {
    message: "Télécharger un reçu",
    description: "Page title for the receipt upload page",
  },
  "receipt.page.description": {
    message:
      "Téléchargez une image ou un PDF de reçu pour enregistrer une transaction dans votre registre",
    description: "Page description for the receipt upload page",
  },
  "receipt.page.parsing": {
    message: "Analyse du reçu par l'IA...",
    description: "Loading message while AI parses the receipt",
  },
  "receipt.page.parsingHint": {
    message: "Cela peut prendre jusqu'à 30 secondes.",
    description: "Hint text shown while AI is parsing the receipt",
  },
  "receipt.page.errorTitle": {
    message: "Une erreur s'est produite",
    description: "Alert title shown when an error occurs",
  },
  "receipt.page.tryAgain": {
    message: "Réessayer",
    description: "Button text to retry after an error",
  },

  // Upload Zone
  "receipt.upload.fileTooLarge": {
    message: "Le fichier est trop volumineux. La taille maximale est de 5MB.",
    description: "Validation error when uploaded file exceeds 5MB size limit",
  },
  "receipt.upload.unsupportedType": {
    message:
      "Type de fichier non pris en charge. Veuillez télécharger un fichier PDF, PNG, JPG, JPEG ou WebP.",
    description: "Validation error when file type is not supported",
  },
  "receipt.upload.uploading": {
    message: "Téléchargement...",
    description: "Status text shown while file is being uploaded",
  },
  "receipt.upload.chooseDifferentFile": {
    message: "Choisir un autre fichier",
    description: "Button text to replace the currently selected file",
  },
  "receipt.upload.dragAndDrop": {
    message: "Glissez-déposez votre reçu ici",
    description: "Instruction text in the drag-and-drop upload zone",
  },
  "receipt.upload.supports": {
    message: "Formats pris en charge : PDF, PNG, JPG, JPEG, WebP — 5MB max.",
    description: "Hint text showing supported file formats and size limit",
  },
  "receipt.upload.chooseFile": {
    message: "Choisir un fichier",
    description: "Button text to open the file picker",
  },

  // Review Form — validation messages
  "receipt.review.dateRequired": {
    message: "La date est obligatoire",
    description: "Validation error when date field is empty",
  },
  "receipt.review.payeeRequired": {
    message: "Le bénéficiaire est obligatoire",
    description: "Validation error when payee field is empty",
  },
  "receipt.review.descriptionRequired": {
    message: "La description est obligatoire",
    description: "Validation error when description field is empty",
  },
  "receipt.review.amountPositive": {
    message: "Le montant doit être un nombre positif",
    description: "Validation error when amount is not a positive number",
  },
  "receipt.review.currencyRequired": {
    message: "La devise est obligatoire",
    description: "Validation error when currency field is empty",
  },
  "receipt.review.expenseAccountRequired": {
    message: "Le compte de dépenses est obligatoire",
    description: "Validation error when expense account is not selected",
  },
  "receipt.review.paymentAccountRequired": {
    message: "Le compte de paiement est obligatoire",
    description: "Validation error when payment account is not selected",
  },
  "receipt.review.documentAccountRequired": {
    message: "Le compte de documents est obligatoire",
    description: "Validation error when document account is not selected",
  },

  // Review Form — labels and placeholders
  "receipt.review.receiptDetails": {
    message: "Détails du reçu",
    description: "Card title for the receipt details section",
  },
  "receipt.review.date": {
    message: "Date",
    description: "Label for the date field",
  },
  "receipt.review.payee": {
    message: "Bénéficiaire",
    description: "Label for the payee field",
  },
  "receipt.review.merchantName": {
    message: "Nom du commerçant",
    description: "Placeholder for the payee input field",
  },
  "receipt.review.description": {
    message: "Description",
    description: "Label for the description field",
  },
  "receipt.review.transactionDescription": {
    message: "Description de la transaction",
    description: "Placeholder for the description input field",
  },
  "receipt.review.amount": {
    message: "Montant",
    description: "Label for the amount field",
  },
  "receipt.review.currency": {
    message: "Devise",
    description: "Label for the currency field",
  },
  "receipt.review.accounts": {
    message: "Comptes",
    description: "Card title for the accounts section",
  },
  "receipt.review.expenseAccount": {
    message: "Compte de dépenses",
    description: "Label for the expense account field",
  },
  "receipt.review.selectExpenseAccount": {
    message: "Sélectionnez le compte de dépenses",
    description: "Placeholder for the expense account combobox",
  },
  "receipt.review.paymentAccount": {
    message: "Compte de paiement",
    description: "Label for the payment account field",
  },
  "receipt.review.selectPaymentAccount": {
    message: "Sélectionnez le compte de paiement",
    description: "Placeholder for the payment account combobox",
  },
  "receipt.review.documentAccount": {
    message: "Compte de documents",
    description: "Label for the document account field",
  },
  "receipt.review.selectDocumentAccount": {
    message: "Sélectionnez le compte de documents",
    description: "Placeholder for the document account combobox",
  },
  "receipt.review.preview": {
    message: "Aperçu",
    description: "Card title for the Beancount transaction preview",
  },
  "receipt.review.uploadDifferentReceipt": {
    message: "Télécharger un autre reçu",
    description: "Button text to go back and upload a different receipt",
  },
  "receipt.review.recordTransaction": {
    message: "Enregistrer la transaction",
    description: "Submit button text to record the transaction",
  },

  // Success Card
  "receipt.success.title": {
    message: "Transaction enregistrée",
    description: "Heading shown after transaction is successfully recorded",
  },
  "receipt.success.description": {
    message: "Votre reçu a été enregistré dans votre registre.",
    description: "Description shown after transaction is successfully recorded",
  },
  "receipt.success.payee": {
    message: "Bénéficiaire",
    description: "Label for payee in the success summary",
  },
  "receipt.success.date": {
    message: "Date",
    description: "Label for date in the success summary",
  },
  "receipt.success.amount": {
    message: "Montant",
    description: "Label for amount in the success summary",
  },
  "receipt.success.expense": {
    message: "Dépense",
    description: "Label for expense account in the success summary",
  },
  "receipt.success.payment": {
    message: "Paiement",
    description: "Label for payment account in the success summary",
  },
  "receipt.success.viewJournal": {
    message: "Voir le journal",
    description: "Button text to navigate to the journal after success",
  },
  "receipt.success.uploadAnother": {
    message: "Télécharger un autre reçu",
    description: "Button text to upload another receipt after success",
  },

  // Workflow error messages
  "receipt.workflow.failedToParse": {
    message: "Échec de l'analyse du reçu",
    description: "Error message when AI fails to parse the receipt",
  },
  "receipt.workflow.failedToRecord": {
    message: "Échec de l'enregistrement de la transaction du reçu",
    description: "Error message when recording the transaction fails",
  },
};

export default frReceipt;
