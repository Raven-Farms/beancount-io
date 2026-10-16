export interface TranslationEntry {
  message: string;
  description: string;
}

const skGalleryPage: Record<string, TranslationEntry> = {
  "page.gallery.minimumSearchCharacters": {
    message: "Zadajte aspoň 2 znaky na vyhľadávanie.",
    description:
      "Polite search status when fewer than two characters have been entered",
  },
  "page.gallery.noMatchingLedgers": {
    message: "Žiadne knihy nezodpovedajú vyhľadávaniu {query}",
    description:
      "Polite status naming the completed search that found no ledgers",
  },
  "page.gallery.ledgersFound_one": {
    message: "Našla sa {count} kniha",
    description:
      "Polite status announcing the number of ledgers found by the completed search",
  },
  "page.gallery.ledgersFound_few": {
    message: "Našli sa {count} knihy",
    description:
      "Polite status announcing the number of ledgers found by the completed search",
  },
  "page.gallery.ledgersFound_many": {
    message: "Našlo sa {count} knihy",
    description:
      "Polite status announcing the number of ledgers found by the completed search",
  },
  "page.gallery.ledgersFound_other": {
    message: "Našlo sa {count} kníh",
    description:
      "Polite status announcing the number of ledgers found by the completed search",
  },
  "page.gallery.failedToSearchLedgers": {
    message: "Vyhľadávanie kníh zlyhalo",
    description: "Error message when search fails",
  },
  "page.gallery.ledgerGallery": {
    message: "Galéria kníh",
    description: "Title for gallery page",
  },
  "page.gallery.ledgerGalleryDescription": {
    message:
      "Objavte a preskúmajte všetky dostupné knihy. Vyhľadávajte podľa názvu pre rýchle nájdenie a navigáciu k akejkoľvek knihe.",
    description: "Description for gallery page",
  },
  "page.gallery.noLedgersFound": {
    message: "Žiadne knihy neboli nájdené",
    description: "Message when user has no ledgers",
  },
  "page.gallery.searchLedgersPlaceholder": {
    message:
      "Vyhľadajte knihy a navigujte k nim. Zadajte aspoň 2 znaky pre vyhľadávanie.",
    description: "Placeholder for ledger search input",
  },
  "page.gallery.tryAdjustingSearchQuery": {
    message: "Skúste upraviť vyhľadávací dotaz pre nájdenie viacerých kníh.",
    description: "Suggestion to adjust search query",
  },
};

export default skGalleryPage;
