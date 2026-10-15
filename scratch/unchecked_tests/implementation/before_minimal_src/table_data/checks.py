"""Check generated rows and preserve ratio values/statuses at storage handoffs."""
import json
from decimal import Decimal

import pandas as pd


def check_ratios(df):
    keys = ["ticker", "fiscal_period_end"]
    if df.duplicated(keys).any():
        raise ValueError("Financial data contains duplicate ticker/period keys")
    for row in df.to_dict('records'):
        evidence = json.loads(row['extraction_evidence']) if 'extraction_evidence' in row else None
        for metric in ('debt_to_assets', 'interest_coverage'):
            value = row[metric + '_ratio']
            missing = value is None or value == '' or (isinstance(value, float) and pd.isna(value))
            number = None if missing else Decimal(str(value))
            if number is not None and not number.is_finite():
                raise ValueError(f'Nonfinite {metric}')
            status = row.get(metric + '_status')
            if status is not None and (number is not None) != (status == 'available'):
                raise ValueError(f'{metric} value/status mismatch')
            if evidence is not None:
                recorded = evidence[metric]
                recorded_value = None if recorded['value'] is None else Decimal(recorded['value'])
                if recorded_value != number or (status is not None and recorded['status'] != status):
                    raise ValueError(f'{metric} evidence mismatch')
