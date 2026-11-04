from app.core.config import settings


def validate_currency(value: str) -> str:
    value = value.upper()
    if value not in settings.supported_currencies:
        raise ValueError(f"Unsupported currency: {value}")
    return value
