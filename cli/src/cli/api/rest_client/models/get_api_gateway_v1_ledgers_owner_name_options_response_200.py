from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="GetApiGatewayV1LedgersOwnerNameOptionsResponse200")


@_attrs_define
class GetApiGatewayV1LedgersOwnerNameOptionsResponse200:
    """
    Attributes:
        title (str):
        name_assets (str):  Example: Assets.
        name_equity (str):  Example: Equity.
        name_expenses (str):  Example: Expenses.
        name_income (str):  Example: Income.
        name_liabilities (str):  Example: Liabilities.
        account_current_conversions (str):  Example: Conversions:Current.
        account_current_earnings (str):  Example: Earnings:Current.
        render_commas (bool):
        operating_currency (list[str]):  Example: ['USD'].
    """

    title: str
    name_assets: str
    name_equity: str
    name_expenses: str
    name_income: str
    name_liabilities: str
    account_current_conversions: str
    account_current_earnings: str
    render_commas: bool
    operating_currency: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        name_assets = self.name_assets

        name_equity = self.name_equity

        name_expenses = self.name_expenses

        name_income = self.name_income

        name_liabilities = self.name_liabilities

        account_current_conversions = self.account_current_conversions

        account_current_earnings = self.account_current_earnings

        render_commas = self.render_commas

        operating_currency = self.operating_currency

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "nameAssets": name_assets,
                "nameEquity": name_equity,
                "nameExpenses": name_expenses,
                "nameIncome": name_income,
                "nameLiabilities": name_liabilities,
                "accountCurrentConversions": account_current_conversions,
                "accountCurrentEarnings": account_current_earnings,
                "renderCommas": render_commas,
                "operatingCurrency": operating_currency,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title = d.pop("title")

        name_assets = d.pop("nameAssets")

        name_equity = d.pop("nameEquity")

        name_expenses = d.pop("nameExpenses")

        name_income = d.pop("nameIncome")

        name_liabilities = d.pop("nameLiabilities")

        account_current_conversions = d.pop("accountCurrentConversions")

        account_current_earnings = d.pop("accountCurrentEarnings")

        render_commas = d.pop("renderCommas")

        operating_currency = cast(list[str], d.pop("operatingCurrency"))

        get_api_gateway_v1_ledgers_owner_name_options_response_200 = cls(
            title=title,
            name_assets=name_assets,
            name_equity=name_equity,
            name_expenses=name_expenses,
            name_income=name_income,
            name_liabilities=name_liabilities,
            account_current_conversions=account_current_conversions,
            account_current_earnings=account_current_earnings,
            render_commas=render_commas,
            operating_currency=operating_currency,
        )

        get_api_gateway_v1_ledgers_owner_name_options_response_200.additional_properties = d
        return get_api_gateway_v1_ledgers_owner_name_options_response_200

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
