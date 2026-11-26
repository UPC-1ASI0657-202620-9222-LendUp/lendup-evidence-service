from decimal import Decimal, InvalidOperation

from app.domain.entities.incident import GuaranteeDecision

CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("9999999999.99")


def money(value) -> Decimal:
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or result > MAX_AMOUNT or result != result.quantize(CENT):
            raise ValueError("Monto inválido")
        return result.quantize(CENT)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Monto inválido") from None


def remaining_guarantee(agreed, previous) -> Decimal:
    return max(Decimal("0.00"), money(agreed) - money(previous))


def validate_decision(decision: GuaranteeDecision, amount, available) -> Decimal:
    amount = money(amount)
    available = money(available)
    valid = (
        (decision == GuaranteeDecision.NONE and amount == 0)
        or (decision == GuaranteeDecision.PARTIAL and 0 < amount < available)
        or (decision == GuaranteeDecision.TOTAL and available > 0 and amount == available)
    )
    if not valid:
        raise ValueError("Decisión y monto incompatibles con la garantía disponible")
    return amount
