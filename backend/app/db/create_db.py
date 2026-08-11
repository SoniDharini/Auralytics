import asyncio
import asyncpg


async def main():
    try:
        conn = await asyncpg.connect(
            user="postgres",
            host="127.0.0.1",
            port=5432,
            database="template1",
        )
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname='influenceos'"
        )
        if not exists:
            await conn.execute("CREATE DATABASE influenceos")
            print("Successfully created native PostgreSQL database 'influenceos'!")
        else:
            print("PostgreSQL database 'influenceos' already exists.")
        await conn.close()
    except Exception as e:
        print("Error connecting to PostgreSQL:", e)


if __name__ == "__main__":
    asyncio.run(main())
