import hashlib

def calculate_hash(self, ) -> str:
    m = hashlib.sha256()
    for asset_id in self._asset_ids:
        m.update(str.encode(asset_id))
    return m.hexdigest()