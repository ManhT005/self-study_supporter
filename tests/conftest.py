import os

# Before importing legacy services: never connect the offline suite to local/cloud data.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.pop("POSTGRES_HOST", None)
