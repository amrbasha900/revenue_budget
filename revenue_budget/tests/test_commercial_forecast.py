"""Calculation tests that don't require invoices, payment entries or real balances."""
import unittest
from collections import defaultdict
from unittest.mock import patch

import frappe

from revenue_budget.commercial_forecast import (
    _spread, _tier_award, calculate_year, forecast,
)


class TestCommercialForecast(unittest.TestCase):
    def tier(self, minimum, maximum, percent, fixed=0):
        return frappe._dict(min_sales=minimum, max_sales=maximum,
                            discount_percentage=percent, fixed_bonus=fixed)

    def test_whole_and_progressive_tiers(self):
        tiers = [self.tier(0, 1000, 1), self.tier(1000, 0, 2, 50)]
        self.assertEqual(_tier_award(1500, tiers, "Whole Band"), 80)
        self.assertEqual(_tier_award(1500, tiers, "Progressive"), 70)

    def test_allocation_preserves_total(self):
        self.assertEqual(sum(amount for _, amount in _spread(
            100.00, [0, 1, 2], {0: 1, 1: 1, 2: 1}
        )), 100.00)

    def test_sales_collection_moves_two_months(self):
        plan = frappe._dict(
            company="Test", customer="C1", fiscal_year="2026",
            debt_age_months=2, currency="EGP", tier_rules=[],
            discount_rules=[frappe._dict(
                rule_code="P10", calculation_type="Percentage", percentage=10,
                base_type="After Item Discount", scope_type="All Items",
                from_month="January", to_month="January",
                settlement_type="With Sales Collection"
            )],
        )
        monthly = defaultdict(lambda: {"gross": 0.0, "after_item_discount": 0.0, "items": []})
        monthly[0] = {
            "gross": 1000, "after_item_discount": 1000,
            "items": [frappe._dict(item_code="A", item_group="G", gross=1000, net=1000)]
        }
        with patch("revenue_budget.commercial_forecast.sales_for_year",return_value=(monthly,1)):
            result=calculate_year(plan)
        self.assertEqual(result["expected_collections"][(2026,2)], 1000)
        self.assertEqual(result["collection_discounts"][(2026,2)], 100)
        self.assertEqual(result["discounts_by_sale_month"][0], 100)

    def test_previous_year_november_and_december_flow_into_new_year(self):
        current = frappe._dict(
            company="Test",customer="C1",fiscal_year="2026",currency="EGP",
            debt_age_months=2,discount_rules=[],tier_rules=[],
        )
        prior = frappe._dict(
            company="Test",customer="C1",fiscal_year="2025",currency="EGP",
            debt_age_months=2,discount_rules=[],tier_rules=[],
        )
        def fake_sales(company, customer, year):
            months = defaultdict(lambda: {"gross":0.0,"after_item_discount":0.0,"items":[]})
            if year == 2025:
                months[10]["after_item_discount"] = 100
                months[11]["after_item_discount"] = 200
            return months,1
        with patch("revenue_budget.commercial_forecast.active_plan",side_effect=lambda *args: prior if args[2]==2025 else current), patch(
            "revenue_budget.commercial_forecast.sales_for_year",side_effect=fake_sales
        ):
            result=forecast("Test","C1",2026)
        self.assertEqual(result["rows"][0]["collections_prior_year"],100)
        self.assertEqual(result["rows"][1]["collections_prior_year"],200)
        self.assertEqual(result["rows"][2]["collections_prior_year"],0)
