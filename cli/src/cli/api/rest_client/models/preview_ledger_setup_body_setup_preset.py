from enum import StrEnum


class PreviewLedgerSetupBodySetupPreset(StrEnum):
    BLANK1 = "blank@1"
    BUSINESS1 = "business@1"
    COMMUNITY1 = "community@1"
    FREELANCE1 = "freelance@1"
    PERSONAL1 = "personal@1"
    PORTFOLIO1 = "portfolio@1"
    RENTAL1 = "rental@1"
    SHARED_EXPENSES1 = "shared-expenses@1"

    def __str__(self) -> str:
        return str(self.value)
