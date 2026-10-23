from enum import StrEnum


class PreviewLedgerSetupBodySetupAccountsItemOpeningState(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    ZERO = "zero"

    def __str__(self) -> str:
        return str(self.value)
