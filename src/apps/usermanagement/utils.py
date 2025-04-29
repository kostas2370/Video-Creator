def check_conditions(password: str) -> bool:
    password_check = [
        lambda s: any(x.isupper() for x in s),
        lambda s: any(x.islower() for x in s),
        lambda s: any(x.isdigit() for x in s),
        lambda s: len(s) >= 8,
    ]

    return all(condition(password) for condition in password_check)
