import asyncio
from database.mongodb import db
from utils.security import hash_password


async def create_admin():
    username = "admin"
    email = "admin@cyberfoxxx.com"
    password = "Admin@123"

    # Check whether admin already exists
    existing_admin = await db.users.find_one({
        "username": username
    })

    if existing_admin:
        print("⚠️ Admin already exists")
        return

    admin = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "role": "admin"
    }

    await db.users.insert_one(admin)

    print("✅ Admin created successfully")
    print(f"Username: {username}")
    print(f"Password: {password}")


if __name__ == "__main__":
    asyncio.run(create_admin())