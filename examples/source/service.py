from validation import normalize


def prepare(raw, gateway):
    item = normalize(raw)
    if item is None:
        return {'status': 'invalid'}
    receipt = gateway.submit(item)
    return {'status': 'sent', 'receipt': receipt}
