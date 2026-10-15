export interface TranslationEntry {
  message: string;
  description: string;
}

const caEvents: Record<string, TranslationEntry> = {
  "page.events.description": {
    message: "Descripció",
    description: "Table column header for description",
  },
  "page.events.events": {
    message: "Esdeveniments",
    description: "Events in the ledger",
  },
  "page.events.eventsCount": {
    message: "Esdeveniments: {filtered} / {total}",
    description: "Count of filtered events out of total",
  },
  "page.events.noEventsFound": {
    message: "No s'han trobat esdeveniments",
    description: "Empty state title when no events exist",
  },
  "page.events.noEventsFoundForLedger": {
    message: "No s'han trobat esdeveniments per a aquest llibre.",
    description: "Empty state description for no events",
  },
  "page.events.noEventsMatchFilters": {
    message: "Cap esdeveniment no coincideix amb els filtres actuals.",
    description: "Message when filters produce no results",
  },
  "page.events.searchEvents": {
    message: "Cerca esdeveniments...",
    description: "Placeholder for event search input",
  },
};

export default caEvents;
