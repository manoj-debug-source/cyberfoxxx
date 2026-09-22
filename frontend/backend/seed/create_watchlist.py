import asyncio

from database.mongodb import db


WATCHLIST_RECORDS = [
    {
        "record_id": "WL-000001",
        "name": "TEST WATCHLIST PERSON",
        "date_of_birth": "1990-01-15",
        "document_number": "P1234567",
        "nationality": "IND",
        "status": "ACTIVE",
        "category": "WATCHLIST"
    },

    {
        "record_id": "BL-000001",
        "name": "BLACKLIST DEMO PERSON",
        "date_of_birth": "1985-05-20",
        "document_number": "X7654321",
        "nationality": "IND",
        "status": "ACTIVE",
        "category": "BLACKLIST"
    }
]


async def main():

    await db.watchlist_records.delete_many({})

    result = await db.watchlist_records.insert_many(
        WATCHLIST_RECORDS
    )

    print(
        f"Inserted {len(result.inserted_ids)} "
        "watchlist records."
    )


if __name__ == "__main__":
    asyncio.run(main())