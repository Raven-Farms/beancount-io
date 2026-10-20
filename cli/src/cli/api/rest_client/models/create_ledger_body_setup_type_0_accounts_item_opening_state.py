from enum import StrEnum


class CreateLedgerBodySetupType0AccountsItemOpeningState(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    ZERO = "zero"

    def __str__(self) -> str:
        return str(self.value)
