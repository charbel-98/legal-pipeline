"""Shared constants for the legal pipeline."""

# Canonical list of legal bodies scraped from workplacerelations.ie.
# Maps human-readable name → body query parameter value used by the search API.
LEGAL_BODIES: dict[str, str] = {
    "Employment Appeals Tribunal": "2",
    "Equality Tribunal": "1",
    "Labour Court": "3",
    "Workplace Relations Commission": "15376",
}

# Ordered list of body names (used where only the name is needed).
ALL_BODY_NAMES: list[str] = list(LEGAL_BODIES.keys())
