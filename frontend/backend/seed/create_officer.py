import asyncio

from database.mongodb import db
from utils.security import hash_password


async def create_officer():
    username = "officer01"
    email = "officer01@cyberfoxxx.com"
    password = "Officer@123"

    existing_officer = await db.users.find_one({
        "username": username
    })

    if existing_officer:
        print("⚠️ Officer already exists")
        return

    officer = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "role": "officer"
    }

    await db.users.insert_one(officer)

    print("✅ Officer created successfully")
    print(f"Username: {username}")
    print(f"Password: {password}")


if __name__ == "__main__":
    asyncio.run(create_officer())
