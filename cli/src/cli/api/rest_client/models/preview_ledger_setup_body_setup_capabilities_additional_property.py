from enum import StrEnum


class PreviewLedgerSetupBodySetupCapabilitiesAdditionalProperty(StrEnum):
    DECLINED = "declined"
    DEFERRED = "deferred"
    ENABLED = "enabled"

    def __str__(self) -> str:
        return str(self.value)
