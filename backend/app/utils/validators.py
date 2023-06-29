def trim_values(cls, v):
    if isinstance(v, str):
        val = v.strip()
        if val == "":
            raise ValueError('value cannot be empty')
        else:
            return val
    return v
