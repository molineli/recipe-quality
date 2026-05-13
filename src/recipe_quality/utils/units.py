SODIUM_MG_PER_SALT_G = 393.4


def salt_g_to_sodium_mg(salt_g: float) -> float:
    """将食盐克数换算为钠毫克数。"""
    return salt_g * SODIUM_MG_PER_SALT_G
