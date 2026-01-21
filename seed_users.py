from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models, auth_utils

def seed_data():
    db = SessionLocal()
    # Create the users table if it doesn't exist
    models.Base.metadata.create_all(bind=engine)

    users = [
        {
            "username": "admin",
            "password": "admin123",
            "role": "admin",
            "full_name": "System Administrator"
        },
        {
            "username": "doctor",
            "password": "doctor123",
            "role": "doctor",
            "full_name": "Dr. John Doe"
        }
    ]

    for user_data in users:
        # Check if user exists
        exists = db.query(models.User).filter(models.User.username == user_data["username"]).first()
        if not exists:
            new_user = models.User(
                username=user_data["username"],
                hashed_password=auth_utils.hash_password(user_data["password"]),
                role=user_data["role"],
                full_name=user_data["full_name"]
            )
            db.add(new_user)
            print(f"Created user: {user_data['username']} ({user_data['role']})")
    
    db.commit()
    db.close()

if __name__ == "__main__":
    seed_data()