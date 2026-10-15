"""Amounts retain the evidence needed to justify arithmetic on disclosed values."""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, localcontext


class SelectionError(ValueError):
    """Source evidence does not support an unambiguous result."""

    def __init__(self, message, code='conflict'):
        super().__init__(message)
        self.code = code


def decimal_value(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise SelectionError('Invalid numeric value', 'invalid_number') from error
    if not result.is_finite():
        raise SelectionError('Nonfinite numeric value', 'invalid_number')
    if len(result.as_tuple().digits) > 60 or abs(result.adjusted()) > 1000:
        raise SelectionError('Numeric precision exceeds supported arithmetic', 'unsupported_precision')
    return result


def accuracy_interval(value, decimals):
    if decimals is None:
        raise SelectionError('Missing decimals metadata', 'missing_accuracy')
    try:
        accuracy = Decimal(str(decimals))
    except InvalidOperation as error:
        raise SelectionError('Invalid decimals metadata', 'missing_accuracy') from error
    if accuracy == Decimal('Infinity'):
        return value, value, accuracy
    if not accuracy.is_finite() or accuracy != accuracy.to_integral_value() or abs(accuracy) > 1000:
        raise SelectionError('Invalid decimals metadata', 'missing_accuracy')
    with localcontext() as context:
        context.prec = 2200
        radius = Decimal(10) ** (-accuracy) / 2
        return value - radius, value + radius, accuracy


@dataclass(frozen=True)
class Amount:
    value: Decimal
    unit: str
    period: tuple  # CIK, start (None for instant), end
    lower: Decimal
    upper: Decimal
    evidence: dict

    def serializable(self):
        return dict(value=str(self.value), currency=self.unit, period=list(self.period),
                    lower=str(self.lower), upper=str(self.upper), evidence=self.evidence)


def calculate_weighted_total(parts, rule):
    """Signed arithmetic with matching contexts and conservative rounding bounds."""
    if not parts or any(amount is None for _, amount in parts):
        return None
    first_amount = parts[0][1]
    unit = first_amount.unit
    period = first_amount.period
    with localcontext() as context:
        context.prec = 2200
        value = Decimal(0)
        lower = Decimal(0)
        upper = Decimal(0)
        for weight, amount in parts:
            if amount.unit != unit or amount.period != period:
                raise SelectionError('Incompatible currency, entity or period', 'incompatible_basis')
            weight = Decimal(weight)
            value += weight * amount.value
            if weight >= 0:
                lower += weight * amount.lower
                upper += weight * amount.upper
            else:
                lower += weight * amount.upper
                upper += weight * amount.lower
        value = decimal_value(value)
    components = []
    for weight, amount in parts:
        components.append(dict(weight=str(weight), amount=amount.serializable()))
    evidence = dict(method=rule, components=components)
    return Amount(value, unit, period, lower, upper, evidence)


def add_amounts(amounts, rule):
    parts = []
    for amount in amounts:
        parts.append((1, amount))
    return calculate_weighted_total(parts, rule)


def subtract_amounts(total, amounts, rule):
    parts = [(1, total)]
    for amount in amounts:
        parts.append((-1, amount))
    return calculate_weighted_total(parts, rule)


def overlaps(left, right):
    return (left.unit == right.unit and left.period == right.period
            and max(left.lower, right.lower) <= min(left.upper, right.upper))


def select_consistent_amount(candidates, label, reported=None):
    """Compare all derivations; overlapping rounding ranges do not pick a unique value."""
    candidates = [c for c in candidates if c is not None]
    if not candidates:
        return reported
    first_amount = candidates[0]
    for candidate in candidates:
        if candidate.unit != first_amount.unit or candidate.period != first_amount.period:
            raise SelectionError('Candidates use incompatible bases', 'incompatible_basis')
    if len(candidates) == 1 and reported is None:
        return candidates[0]
    lower = max(c.lower for c in candidates)
    upper = min(c.upper for c in candidates)
    if lower > upper:
        raise SelectionError(f'{label}: calculation equations disagree beyond rounding')
    if reported is not None:
        if any(not overlaps(reported, c) for c in candidates):
            raise SelectionError(f'{label}: independent reported amount fails reconciliation')
        return Amount(reported.value, reported.unit, reported.period, reported.lower, reported.upper,
                      dict(method='independent_reported_reconciliation', reported=reported.serializable(),
                           checks=[c.serializable() for c in candidates]))
    values = {c.value for c in candidates}
    if len(values) != 1:
        raise SelectionError(f'{label}: rounding-compatible equations do not identify one disclosed arithmetic result',
                             'rounding_ambiguity')
    candidate = candidates[0]
    return Amount(candidate.value, candidate.unit, candidate.period, lower, upper,
                  dict(method='agreed_derivations', derivations=[c.serializable() for c in candidates]))


def uses_reported(amount, concept):
    """Does this derivation depend on a reported fact for the named concept?"""
    pending = [amount.evidence]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            if node.get('method') == 'reported' and node.get('concept') == concept:
                return True
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return False


# SEC Guide 9.10: selecting consistent repeated reported amounts.
def reported_selection(matches, concept, period_end):
    label = f'{concept} at {period_end}'
    units = {row.get('unit_ref') for row in matches}
    if not units or any(not unit for unit in units):
        raise SelectionError(f'{label}: missing unit metadata', 'incompatible_basis')
    if len(units) != 1:
        raise SelectionError(f'{label}: matching facts use different units', 'incompatible_basis')
    lower, upper = Decimal('-Infinity'), Decimal('Infinity')
    by_accuracy = {}
    selected = None
    best = Decimal('-Infinity')
    for row in matches:
        value = decimal_value(row['value'])
        fact_lower, fact_upper, accuracy = accuracy_interval(value, row.get('decimals'))
        if accuracy in by_accuracy and by_accuracy[accuracy] != value:
            raise SelectionError(f'{label}: differing amounts have equal declared accuracy')
        by_accuracy[accuracy] = value
        lower = max(lower, fact_lower)
        upper = min(upper, fact_upper)
        if accuracy > best:
            selected = value
            best = accuracy
    if lower > upper:
        raise SelectionError(f'{label}: differing amounts cannot be explained by declared rounding')
    return selected, lower, upper


@dataclass
class RatioResult:
    value: Decimal | None
    status: str
    reason: str = ''
    evidence: dict = field(default_factory=dict)

    def serializable(self):
        value = None
        if self.value is not None:
            value = str(self.value)
        return dict(value=value, status=self.status, reason=self.reason, evidence=self.evidence)
