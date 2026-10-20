from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteBody")


@_attrs_define
class PostApiGatewayV1LedgersOwnerNameEntrySourceDeleteBody:
    """
    Attributes:
        entry_hash (str):
        sha256sum (str):
        allow_invalid (bool | Unset): Commit even when the write would add bean-check errors (VALIDATION_FAILED with
            newLedgerErrors), instead of refusing it.
    """

    entry_hash: str
    sha256sum: str
    allow_invalid: bool | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        entry_hash = self.entry_hash

        sha256sum = self.sha256sum

        allow_invalid = self.allow_invalid

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "entryHash": entry_hash,
                "sha256sum": sha256sum,
            }
        )
        if allow_invalid is not UNSET:
            field_dict["allowInvalid"] = allow_invalid

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        entry_hash = d.pop("entryHash")

        sha256sum = d.pop("sha256sum")

        allow_invalid = d.pop("allowInvalid", UNSET)

        post_api_gateway_v1_ledgers_owner_name_entry_source_delete_body = cls(
            entry_hash=entry_hash,
            sha256sum=sha256sum,
            allow_invalid=allow_invalid,
        )

        return post_api_gateway_v1_ledgers_owner_name_entry_source_delete_body
