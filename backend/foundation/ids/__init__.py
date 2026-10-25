import uuid
def uid(prefix: str = "id") -> str:
    return prefix + "_" + uuid.uuid4().hex
