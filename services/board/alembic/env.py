import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool, text

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ["DATABASE_URL"]
config.set_main_option("sqlalchemy.url", database_url)

# No ORM models / declarative Base yet — migrations are written by hand for now.
target_metadata = None

# Alembic needs this schema to exist before it can create/check its own
# version-tracking table in it (version_table_schema below) — it can't wait
# for the first migration's own CREATE SCHEMA to run, since Alembic tries to
# ensure the version table exists first. Created here, ahead of everything
# else, so a brand-new database needs no manual bootstrap step (Decision #34).
VERSION_SCHEMA = "board"


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=VERSION_SCHEMA,
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
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {VERSION_SCHEMA}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=VERSION_SCHEMA,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
