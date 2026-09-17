import re


def normalize_description(description):
    description = str(description)

    # Convert to uppercase
    description = description.upper()

    # Replace symbols with spaces
    description = re.sub(r"[^A-Z0-9 ]", " ", description)

    # Remove extra spaces
    description = re.sub(r"\s+", " ", description)

    return description.strip()