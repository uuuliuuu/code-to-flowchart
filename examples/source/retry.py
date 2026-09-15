def fetch_first(keys, client, audit):
    for key in keys:
        if not key:
            continue
        for attempt in range(3):
            try:
                result = client.fetch(key)
                if result is None:
                    break
                return result
            except TimeoutError:
                if attempt == 2:
                    raise
            finally:
                audit(key, attempt)
    return None
