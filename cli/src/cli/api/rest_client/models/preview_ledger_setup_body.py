from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.preview_ledger_setup_body_setup import PreviewLedgerSetupBodySetup


T = TypeVar("T", bound="PreviewLedgerSetupBody")


@_attrs_define
class PreviewLedgerSetupBody:
    """
    Attributes:
        setup (PreviewLedgerSetupBodySetup):
    """

    setup: PreviewLedgerSetupBodySetup

    def to_dict(self) -> dict[str, Any]:
        setup = self.setup.to_dict()

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "setup": setup,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.preview_ledger_setup_body_setup import PreviewLedgerSetupBodySetup  # noqa: PLC0415

        d = dict(src_dict)
        setup = PreviewLedgerSetupBodySetup.from_dict(d.pop("setup"))

        preview_ledger_setup_body = cls(
            setup=setup,
        )

        return preview_ledger_setup_body
