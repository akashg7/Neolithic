"""One canonical phone format for auth: the 10-digit Indian mobile number.

The app sends "+919822011111", a tester may type "9822011111" or
"098220 11111"; all three are the same farmer. OTP rows and users are keyed
on the canonical form, so a code requested as one spelling verifies as another.
"""
import re


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return digits
