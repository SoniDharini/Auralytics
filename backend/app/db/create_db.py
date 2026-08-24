import asyncio

import asyncpg
from sqlalchemy.engine import make_url

from app.core.config import settings


async def main():
    url = make_url(settings.DATABASE_URL)

    if url.get_backend_name() != "postgresql":
        print(f"DATABASE_URL is not PostgreSQL ({url.get_backend_name()}); nothing to create.")
        return

    database = url.database
    try:
        # template1 is always present, so it is a safe entry point for CREATE DATABASE.
        conn = await asyncpg.connect(
            user=url.username,
            password=url.password,
            host=url.host or "127.0.0.1",
            port=url.port or 5432,
            database="template1",
        )
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname=$1", database
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{database}"')
            print(f"Successfully created PostgreSQL database '{database}'!")
        else:
            print(f"PostgreSQL database '{database}' already exists.")
        await conn.close()
    except Exception as e:
        print("Error connecting to PostgreSQL:", e)


if __name__ == "__main__":
    asyncio.run(main())
