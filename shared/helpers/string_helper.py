
def strtobool(value: str) -> bool:
    """Convert a boolean string into bool

    Args:
        value (str): the string value

    Returns:
        bool: the boolean representation
    """
    return str(value).lower() in ['yes', 'true', True]