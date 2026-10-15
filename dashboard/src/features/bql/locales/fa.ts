export interface TranslationEntry {
  message: string;
  description: string;
}

const faBql: Record<string, TranslationEntry> = {
  "bql.executeQuery": {
    message: "اجرای پرسمان",
    description: "Button text to execute query",
  },
  "bql.executing": {
    message: "در حال اجرا...",
    description: "Button text when query is executing",
  },
  "bql.queryShortcutHint": {
    message:
      "برای اجرای پرسمان Cmd+Enter (مک) یا Ctrl+Enter (ویندوز/لینوکس) را فشار دهید",
    description: "Hint text for query keyboard shortcut",
  },
  "bql.queryHistory": {
    message: "تاریخچه پرسمان‌ها",
    description: "Section title for query history",
  },
  "bql.downloadCSV": {
    message: "دانلود CSV",
    description: "Button text to download query results as CSV",
  },
  "bql.noQueryHistory": {
    message:
      "هنوز پرسمانی اجرا نشده است. برای شروع پرسمانی را در بالا وارد کنید.",
    description: "Empty state message when no queries have been executed",
  },
  "bql.deleteQuery": {
    message: "حذف پرسمان",
    description: "Button text to delete a query from history",
  },
  "bql.rowCount": {
    message: "ردیف‌ها: {count}",
    description: "Row count for large query results",
  },
  "bql.errors.unknownColumn": {
    message:
      "ستون ناشناخته «{column}». املای آن را با ستون‌هایی که این پرس‌وجو می‌تواند انتخاب کند بررسی کنید.",
    description:
      "Query error naming a column the query referenced that does not exist; {column} is the identifier from the query",
  },
  "bql.errors.syntaxError": {
    message:
      "خطای نحوی نزدیک «{token}» در نویسه {position}. پرس\u200cوجو را از همان نقطه بررسی کنید.",
    description:
      "Query error for a BQL parse failure; {token} is the unexpected token and {position} its 1-based character position in the query",
  },
  "page.bql.query": {
    message: "پرس‌وجو",
    description: "Sidebar navigation label for the BQL query page",
  },
  "page.bql.queryResult": {
    message: "نتیجه پرس‌وجو",
    description: "Label for a query result section header",
  },
  "page.bql.unknownResultType": {
    message: "نوع نتیجه نامشخص",
    description: "Message when query result type is not recognized",
  },
  "page.bql.noDataReturnedFromQuery": {
    message: "پرس‌وجو هیچ داده‌ای برنگرداند",
    description: "Message when a query returns no data",
  },
};

export default faBql;
