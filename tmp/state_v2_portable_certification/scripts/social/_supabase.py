"""Offline adapter stub for isolated State v2 tests."""
def configured():
    return False

def rest(*args, **kwargs):
    raise RuntimeError("PRODUCTION_SUPABASE_DISABLED_IN_CERTIFICATION_BUNDLE")
