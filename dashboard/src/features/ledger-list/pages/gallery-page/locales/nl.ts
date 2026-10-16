export interface TranslationEntry {
  message: string;
  description: string;
}

const nlGalleryPage: Record<string, TranslationEntry> = {
  "page.gallery.minimumSearchCharacters": {
    message: "Typ minimaal 2 tekens om te zoeken.",
    description:
      "Polite search status when fewer than two characters have been entered",
  },
  "page.gallery.noMatchingLedgers": {
    message: "Geen grootboeken komen overeen met {query}",
    description:
      "Polite status naming the completed search that found no ledgers",
  },
  "page.gallery.ledgersFound_one": {
    message: "{count} grootboek gevonden",
    description:
      "Polite status announcing the number of ledgers found by the completed search",
  },
  "page.gallery.ledgersFound_other": {
    message: "{count} grootboeken gevonden",
    description:
      "Polite status announcing the number of ledgers found by the completed search",
  },
  "page.gallery.failedToSearchLedgers": {
    message: "Grootboeken zoeken mislukt",
    description: "Error message when search fails",
  },
  "page.gallery.ledgerGallery": {
    message: "Grootboek galerij",
    description: "Title for gallery page",
  },
  "page.gallery.ledgerGalleryDescription": {
    message:
      "Ontdek en verken alle beschikbare grootboeken. Zoek op naam om snel grootboeken te vinden en te openen.",
    description: "Description for gallery page",
  },
  "page.gallery.noLedgersFound": {
    message: "Geen grootboeken gevonden",
    description: "Message when user has no ledgers",
  },
  "page.gallery.searchLedgersPlaceholder": {
    message:
      "Zoek naar grootboeken en navigeer ernaar. Typ minimaal 2 tekens om te zoeken.",
    description: "Placeholder for ledger search input",
  },
  "page.gallery.tryAdjustingSearchQuery": {
    message: "Pas uw zoekopdracht aan om meer grootboeken te vinden.",
    description: "Suggestion to adjust search query",
  },
};

export default nlGalleryPage;
