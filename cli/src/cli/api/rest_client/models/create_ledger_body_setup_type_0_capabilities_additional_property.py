from enum import StrEnum


class CreateLedgerBodySetupType0CapabilitiesAdditionalProperty(StrEnum):
    DECLINED = "declined"
    DEFERRED = "deferred"
    ENABLED = "enabled"

    def __str__(self) -> str:
        return str(self.value)
