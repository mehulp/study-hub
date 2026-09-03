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
# else, so a brand-new database needs no manual bootstrap step.
VERSION_SCHEMA = "auth"


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Scoped to this service's own schema — on a shared Postgres
        # instance (Decision #13), the default unscoped `public.alembic_version`
        # would be shared across every service's migration history, defeating
        # Decision #19's "one independent history per service."
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

        # One-time self-heal for a database whose Auth history predates
        # Decision #34 — previously tracked in the default, unscoped
        # `public.alembic_version`. Without this, Alembic sees no history in
        # `auth.alembic_version` and tries to re-run migration 0001 against
        # tables that already exist, breaking `upgrade head` on every
        # already-migrated database (only a truly fresh one self-heals
        # without this step). Auth-specific: Items/Board were both created
        # after this fix existed, so they never had a legacy unscoped table.
        legacy_exists = connection.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'alembic_version')"
            )
        ).scalar()
        new_exists = connection.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                f"WHERE table_schema = '{VERSION_SCHEMA}' AND table_name = 'alembic_version')"
            )
        ).scalar()
        if legacy_exists and not new_exists:
            connection.execute(
                text(
                    f"CREATE TABLE {VERSION_SCHEMA}.alembic_version "
                    "(LIKE public.alembic_version INCLUDING ALL)"
                )
            )
            connection.execute(
                text(f"INSERT INTO {VERSION_SCHEMA}.alembic_version SELECT * FROM public.alembic_version")
            )
            connection.execute(text("DROP TABLE public.alembic_version"))

        # Required even when the `if` above didn't run: the two SELECTs
        # above still implicitly opened a transaction on this connection
        # (SQLAlchemy 2.0 "autobegin" behavior) that nothing else commits.
        # Left open, it would silently roll back everything Alembic does
        # next when the connection closes at the end of this function —
        # a real bug this exact code hit and was caught on first test.
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
