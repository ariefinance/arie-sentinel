"""Reset only the dedicated fixture-backed management-demo dataset."""

from sqlalchemy import text

from arie_sentinel.config import Settings
from arie_sentinel.db import engine
from arie_sentinel.models import Base

settings = Settings()
if settings.env.lower() != "demo" or settings.provider_mode != "fixture":
    raise SystemExit("Demo reset requires ARIE_ENV=demo and ARIE_PROVIDER_MODE=fixture")

table_names = ", ".join(
    engine.dialect.identifier_preparer.quote(table.name) for table in Base.metadata.sorted_tables
)
with engine.begin() as connection:
    connection.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))

print("Reset the non-live management-demo dataset.")
