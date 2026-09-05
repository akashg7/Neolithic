def paise_to_rupees(paise: int) -> str:
    """Format paise as ₹ string. For display only — never use in calculations."""
    return f"₹{paise / 100:.2f}"


def rupees_to_paise(rupees: float) -> int:
    """Convert rupees to paise. Use only for data ingestion, never internal math."""
    return int(round(rupees * 100))
