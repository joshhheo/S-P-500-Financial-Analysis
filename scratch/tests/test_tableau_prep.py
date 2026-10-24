"""Offline export-query checks using SQLite with percentile substitutes.

Dates use integer ordinals to exercise PostgreSQL-style date subtraction.
These checks cover comparison rules, not live PostgreSQL behavior or precision.
"""
import math
import sqlite3
import unittest
from datetime import date
from pathlib import Path

SQL_FOLDER = Path(__file__).resolve().parents[2] / 'src/database/sql/tableau_prep'
METRICS = [
    'liabilities_to_assets_ratio',
    'interest_coverage_ratio',
]


class Percentile25:
    fraction = 0.25

    def __init__(self):
        self.values = []

    def step(self, value):
        if value is not None:
            self.values.append(value)

    def finalize(self):
        if not self.values:
            return None
        values = sorted(self.values)
        position = (len(values) - 1) * self.fraction
        lower = math.floor(position)
        upper = math.ceil(position)
        return values[lower] + (values[upper] - values[lower]) * (position - lower)


class Percentile50(Percentile25):
    fraction = 0.5


class Percentile75(Percentile25):
    fraction = 0.75


def ordinal(value):
    if value is None:
        return None
    return date.fromisoformat(value).toordinal()


def export_rows(metric, current, history, inactive=()):
    with sqlite3.connect(':memory:') as connection:
        connection.row_factory = sqlite3.Row
        percentiles = [('0.25', Percentile25), ('0.5', Percentile50), ('0.75', Percentile75)]
        query = (SQL_FOLDER / (metric.removesuffix('_ratio') + '_distribution.sql')).read_text()
        for fraction, aggregate in percentiles:
            name = aggregate.__name__
            connection.create_aggregate(name, 1, aggregate)
            expression = f'PERCENTILE_CONT({fraction}) WITHIN GROUP (\n            ORDER BY {metric}\n        )::NUMERIC'
            assert expression in query
            query = query.replace(expression, f'{name}({metric})')
        connection.execute('''CREATE TABLE companies (
            ticker TEXT PRIMARY KEY, company_name TEXT, sector TEXT,
            is_current_constituent BOOLEAN
        )''')
        connection.execute(f'''CREATE TABLE financials (
            ticker TEXT, fiscal_period_start INTEGER, fiscal_period_end INTEGER,
            {metric} REAL, PRIMARY KEY (ticker, fiscal_period_end)
        )''')
        for ticker in {row[0] for row in current + history}:
            connection.execute('INSERT INTO companies VALUES (?, ?, ?, ?)',
                               (ticker, ticker, 'Example sector', ticker not in inactive))
        for ticker, start, end, ratio in current + history:
            connection.execute('INSERT INTO financials VALUES (?, ?, ?, ?)',
                               (ticker, ordinal(start), ordinal(end), ratio))
        return {(row['ticker'], row['comparison_period']): dict(row)
                for row in connection.execute(query)}


class AnnualComparisonTests(unittest.TestCase):
    def test_latest_period_selected_before_filtering_and_former_members_excluded(self):
        current = [
            ('VALID', '2025-01-01', '2025-12-31', 0.6),
            ('LATEST_NULL', '2025-01-01', '2025-12-31', None),
            ('FORMER', '2025-01-01', '2025-12-31', 0.6),
        ]
        history = [
            ('VALID', '2024-01-01', '2024-12-31', 0.5),
            ('LATEST_NULL', '2024-01-01', '2024-12-31', 0.5),
            ('LATEST_NULL', '2023-01-01', '2023-12-31', 0.4),
            ('FORMER', '2024-01-01', '2024-12-31', 0.5),
        ]
        for metric in METRICS:
            with self.subTest(metric=metric):
                rows = export_rows(metric, current, history, inactive=('FORMER',))
                self.assertEqual(set(rows), {('VALID', 'Previous'), ('VALID', 'Latest')})
                self.assertEqual(rows[('VALID', 'Latest')][metric], 0.6)

    def test_calendar_and_52_53_week_years(self):
        current = [
            ('CAL', '2025-01-01', '2025-12-31', 0.66),
            ('WEEK', '2024-09-01', '2025-08-30', 0.4),
        ]
        history = [
            ('CAL', '2024-01-01', '2024-12-31', 0.6),
            ('WEEK', '2023-08-27', '2024-08-31', 0.5),
        ]
        for metric in METRICS:
            with self.subTest(metric=metric):
                rows = export_rows(metric, current, history)
                change = metric.removesuffix('_ratio') + '_change'
                self.assertEqual(len(rows), 4)
                self.assertAlmostEqual(rows[('CAL', 'Latest')][change], 10)
                self.assertAlmostEqual(rows[('WEEK', 'Latest')][change], -20)
                self.assertEqual(rows[('CAL', 'Latest')][metric], 0.66)
                self.assertEqual(rows[('CAL', 'Previous')][metric], 0.6)
                self.assertEqual(rows[('CAL', 'Previous')]['fiscal_period_end'], ordinal('2024-12-31'))
                self.assertIsNone(rows[('CAL', 'Previous')][change])

    def test_missing_ratios_and_history_exclude_both_periods_without_fallback(self):
        current = [
            ('GAP', '2025-01-01', '2025-12-31', 0.6),
            ('PRIOR_NULL', '2025-01-01', '2025-12-31', 0.6),
            ('CURRENT_NULL', '2025-01-01', '2025-12-31', None),
            ('DATE_NULL', None, '2025-12-31', 0.6),
        ]
        history = [
            ('GAP', '2023-01-01', '2023-12-31', 0.4),
            ('PRIOR_NULL', '2024-01-01', '2024-12-31', None),
            ('PRIOR_NULL', '2023-01-01', '2023-12-31', 0.4),
            ('CURRENT_NULL', '2024-01-01', '2024-12-31', 0.4),
        ]
        for metric in METRICS:
            with self.subTest(metric=metric):
                rows = export_rows(metric, current, history)
                self.assertEqual(rows, {})

    def test_nonpositive_baselines_and_crossing_zero(self):
        current = [(ticker, '2025-01-01', '2025-12-31', ratio)
                   for ticker, ratio in [('ZERO', 1), ('NEGATIVE', 1), ('CROSS', -1)]]
        history = [(ticker, '2024-01-01', '2024-12-31', ratio)
                   for ticker, ratio in [('ZERO', 0), ('NEGATIVE', -2), ('CROSS', 2)]]
        for metric in METRICS:
            with self.subTest(metric=metric):
                rows = export_rows(metric, current, history)
                change = metric.removesuffix('_ratio') + '_change'
                self.assertIsNone(rows[('ZERO', 'Latest')][change])
                self.assertIsNone(rows[('NEGATIVE', 'Latest')][change])
                self.assertAlmostEqual(rows[('CROSS', 'Latest')][change], -150)
                self.assertEqual(len(rows), 6)
                self.assertEqual(rows[('ZERO', 'Previous')][metric], 0)
                self.assertEqual(rows[('NEGATIVE', 'Previous')][metric], -2)
                for (ticker, period), row in rows.items():
                    if period == 'Previous':
                        self.assertIsNone(row[change])

    def test_transition_periods_and_nonconsecutive_dates_are_not_annual_matches(self):
        current = [
            ('SHORT_CURRENT', '2025-07-01', '2025-12-31', 0.6),
            ('SHORT_PRIOR', '2025-01-01', '2025-12-31', 0.6),
            ('ONE_DAY_GAP', '2025-01-01', '2025-12-31', 0.6),
        ]
        history = [
            ('SHORT_CURRENT', '2024-07-01', '2025-06-30', 0.4),
            ('SHORT_PRIOR', '2024-07-01', '2024-12-31', 0.4),
            ('ONE_DAY_GAP', '2024-01-01', '2024-12-30', 0.4),
        ]
        for metric in METRICS:
            with self.subTest(metric=metric):
                rows = export_rows(metric, current, history)
                self.assertEqual(rows, {})

    def test_quartiles_and_distances_are_separate_for_each_period(self):
        current = [(f'T{index}', '2025-01-01', '2025-12-31', value)
                   for index, value in enumerate([10, 20, 30, 40, 200])]
        history = [(f'T{index}', '2024-01-01', '2024-12-31', value)
                   for index, value in enumerate([1, 2, 3, 4, 5])]
        for metric in METRICS:
            with self.subTest(metric=metric):
                rows = export_rows(metric, current, history)
                self.assertEqual(len(rows), 10)
                self.assertAlmostEqual(rows[('T4', 'Latest')]['median_distance_iqr'], 8.5)
                self.assertAlmostEqual(rows[('T4', 'Previous')]['median_distance_iqr'], 1)
                self.assertEqual(rows[('T2', 'Latest')]['median_distance_iqr'], 0)
                self.assertEqual(rows[('T2', 'Previous')]['median_distance_iqr'], 0)

    def test_zero_iqr_preserves_rows_with_null_distance(self):
        current = [(ticker, '2025-01-01', '2025-12-31', 2) for ticker in ['A', 'B']]
        history = [(ticker, '2024-01-01', '2024-12-31', 1) for ticker in ['A', 'B']]
        for metric in METRICS:
            with self.subTest(metric=metric):
                rows = export_rows(metric, current, history)
                self.assertEqual(len(rows), 4)
                for row in rows.values():
                    self.assertIsNone(row['median_distance_iqr'])
