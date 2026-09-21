"""JurisGround public API."""

from .gate import verify_claim, verify_batch
from .legal import PolishLegalCitation, parse_polish_citations
from .models import Claim, ClaimResult, Policy, Source

__all__ = [
    "Claim",
    "ClaimResult",
    "Policy",
    "PolishLegalCitation",
    "Source",
    "parse_polish_citations",
    "verify_batch",
    "verify_claim",
]
__version__ = "0.3.0"
