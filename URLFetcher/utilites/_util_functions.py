import hashlib

"""
This file is for general utiltiies that can be used anywhere in the application
"""
def url_to_hash(url):
        # Hash the URL - truncate to 16 characters for reduced size
        return hashlib.sha256(url.encode()).hexdigest()[:16]
        pass