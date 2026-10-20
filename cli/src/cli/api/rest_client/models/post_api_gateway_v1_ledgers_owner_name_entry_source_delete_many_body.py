from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_api_gateway_v1_ledgers_owner_name_entry_source_delete_many_body_entries_item import (
        PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteManyBodyEntriesItem,
    )


T = TypeVar("T", bound="PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteManyBody")


@_attrs_define
class PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteManyBody:
    """
    Attributes:
        entries (list[PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteManyBodyEntriesItem]):
        allow_invalid (bool | Unset): Commit even when the write would add bean-check errors (VALIDATION_FAILED with
            newLedgerErrors), instead of refusing it.
    """

    entries: list[PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteManyBodyEntriesItem]
    allow_invalid: bool | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        entries = []
        for entries_item_data in self.entries:
            entries_item = entries_item_data.to_dict()
            entries.append(entries_item)

        allow_invalid = self.allow_invalid

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "entries": entries,
            }
        )
        if allow_invalid is not UNSET:
            field_dict["allowInvalid"] = allow_invalid

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_api_gateway_v1_ledgers_owner_name_entry_source_delete_many_body_entries_item import (
            PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteManyBodyEntriesItem,  # noqa: PLC0415
        )

        d = dict(src_dict)
        entries = []
        _entries = d.pop("entries")
        for entries_item_data in _entries:
            entries_item = PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteManyBodyEntriesItem.from_dict(
                entries_item_data
            )

            entries.append(entries_item)

        allow_invalid = d.pop("allowInvalid", UNSET)

        post_api_gateway_v1_ledgers_owner_name_entry_source_delete_many_body = cls(
            entries=entries,
            allow_invalid=allow_invalid,
        )

        return post_api_gateway_v1_ledgers_owner_name_entry_source_delete_many_body
