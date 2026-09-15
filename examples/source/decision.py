def shipping_cost(total, member):
    if total < 0:
        return None
    if member or total >= 100:
        return 0
    return 8
