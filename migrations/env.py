import sys
from pathlib import Path

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the project root importable (`app.*`) — alembic does not read pyproject's
# pythonpath setting.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL priority: alembic.ini (-x/CLI/tests override) → application settings.
db_url = config.get_main_option("sqlalchemy.url")
if not db_url:
    from app.shared.config import get_settings

    db_url = get_settings().database_url
    config.set_main_option("sqlalchemy.url", db_url)

from app.shared.db import Base  # noqa: E402

import app.products.models  # noqa: E402,F401  (register models on Base.metadata)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
