import vendor_api

PAGE_SIZE = 200


def sync_all():
    orders = []
    offset = 0
    while True:
        page = vendor_api.fetch_orders(offset, PAGE_SIZE)
        orders.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += len(page)
    return orders


def total_amount():
    return sum(order["amount"] for order in sync_all())
