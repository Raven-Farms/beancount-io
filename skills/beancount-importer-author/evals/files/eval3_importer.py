"""Chase checking CSV importer (format generation 1: Date,Description,Amount)."""

import hashlib
import unicodedata

from beangulp.importers import csvbase


class Importer(csvbase.Importer):
    date = csvbase.Date("Date", "%m/%d/%Y")
    narration = csvbase.Column("Description")
    amount = csvbase.Amount("Amount")

    def identify(self, filepath):
        try:
            with open(filepath, encoding=self.encoding) as f:
                return f.readline().strip() == "Date,Description,Amount"
        except (UnicodeDecodeError, OSError):
            return False

    def finalize(self, txn, row):
        posting = txn.postings[0]
        exact = format(posting.units.number.normalize(), "f")
        description = unicodedata.normalize("NFC", " ".join(txn.narration.upper().split()))
        base = f"{txn.date}|{exact} {posting.units.currency}|{description}|{posting.account}"
        txn.meta["import-id"] = "csv:sha256:" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
        return txn


if __name__ == "__main__":
    from beangulp.testing import main

    main(Importer("Assets:Bank:Checking", "USD"))
