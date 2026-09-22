import asyncio

from database.mongodb import db
from database.mongodb import (
    connect_to_mongodb,
    close_mongodb_connection,
)


async def main():
    await connect_to_mongodb()

    screening = await db.screenings.find_one(
        {"screening_id": "SCR-98F39196"},
        {
            "_id": 0,
            "screening_id": 1,
            "scan_id": 1,
            "filename": 1,
            "status": 1,
        },
    )

    print("\n==============================")
    print("SCREENING RESULT")
    print("==============================")
    print(screening)
    print("==============================\n")

    await close_mongodb_connection()


if __name__ == "__main__":
    asyncio.run(main())
