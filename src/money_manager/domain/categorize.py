"""Category rules: a keyword in a description picks the category (pure, deterministic).

A rule maps a keyword to a category of one kind (income or expense). A
description matches when it contains the keyword as whole words, ignoring case,
accents and punctuation; when several rules match, the longest keyword wins
(the most specific), then the oldest rule.

Rules are learned from the user's own corrections: the keyword is the first
meaningful word of the description, skipping what banks add around the payee
(card and transfer prefixes, dates, numbers, card fragments, cities).
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from money_manager.domain.enums import CategoryKind

MIN_KEYWORD_LENGTH = 3
MAX_KEYWORD_LENGTH = 60

# Words banks put around the payee; never useful as a keyword on their own.
_NOISE = frozenset("""
cb carte card paiement payment achat purchase retrait withdrawal dab atm prlv prelevement
sepa vir virement transfer recu emis instantane instant cheque chq frais fees commission
de du des la le les et en au aux a pour par sur from to the of and ref reference facture
operation op date le no num numero tpe pos visa mastercard debit credit www com ma fr
casa casablanca rabat marrakech tanger fes agadir maroc morocco
""".split())


@dataclass(frozen=True, slots=True)
class CategoryRule:
    id: int
    keyword: str  # normalised: lower case, no accents, single spaces
    category_id: int
    kind: CategoryKind


def normalize(text: str) -> str:
    """Lower case, accents removed, every run of non-letters/digits one space."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


def learn_keyword(description: str) -> str | None:
    """The keyword a correction teaches: the description's first meaningful word."""
    for word in normalize(description).split():
        if len(word) < MIN_KEYWORD_LENGTH or word in _NOISE or any(c.isdigit() for c in word):
            continue
        return word
    return None


def clean_keyword(text: str) -> str | None:
    """A keyword typed by hand, normalised; None when it is too short or too long."""
    keyword = normalize(text)
    if len(keyword) < MIN_KEYWORD_LENGTH - 1 or len(keyword) > MAX_KEYWORD_LENGTH:
        return None
    return keyword


def match(description: str, kind: CategoryKind,
          rules: Iterable[CategoryRule]) -> CategoryRule | None:
    """The most specific rule of ``kind`` whose keyword is in the description."""
    padded = f" {normalize(description)} "
    best: CategoryRule | None = None
    for rule in rules:
        if rule.kind is not kind or f" {rule.keyword} " not in padded:
            continue
        if best is None or (len(rule.keyword), -rule.id) > (len(best.keyword), -best.id):
            best = rule
    return best
