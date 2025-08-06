
#mongodb code 

# mutations.py
# Libraries to install:
# pip install strawberry-graphql-fastapi bcrypt pymongo "pydantic[email]"

import bcrypt
import strawberry
from typing import List, Optional, Union
from datetime import datetime
from bson import ObjectId
from pymongo.errors import PyMongoError
from pydantic import ValidationError

# Import the database connection and Pydantic models
from db import users_collection, logins_collection, usertypes_collection
from models import UserModel, LoginModel, UserTypeModel

# --- GraphQL Types ---

@strawberry.type
class UserTypeType:
    id: str = strawberry.field(name="_id")
    usertype: str = strawberry.field(name="usertype")  # Assuming your field is 'usertype'
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.type
class UserType:
    id: str = strawberry.field(name="_id")
    name: str
    email: str
    phone: str
    usertype_id: str
    is_active: bool = strawberry.field(name="isActive")
    is_deleted: bool = strawberry.field(name="isDeleted")
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.input
class UserInput:
    name: str
    email: str
    phone: str
    password: str

# ✅ New: Unified response type for mutations
@strawberry.type
class UserResponse:
    status: int
    message: str
    data: Optional[UserType] = None

# --- GraphQL Queries ---
@strawberry.type
class Query:
    @strawberry.field
    def all_users(self) -> List[UserType]:
        try:
            users = list(users_collection.find({"is_deleted": False}))
            return [
                UserType(
                    id=str(user["_id"]),
                    name=user["name"],
                    email=user["email"],
                    phone=user["phone"],
                    usertype_id=str(user["usertype_id"]),
                    is_active=user["is_active"],
                    is_deleted=user["is_deleted"],
                    created_at=user["created_at"]
                ) for user in users
            ]
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []

    @strawberry.field
    def all_user_types(self) -> List[UserTypeType]:
        try:
            usertypes = list(usertypes_collection.find())
            return [
                UserTypeType(
                    id=str(ut["_id"]),
                    usertype=ut["usertype"],
                    created_at=ut["createdAt"]
                ) for ut in usertypes
            ]
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []

    @strawberry.field
    def user(self, user_id: str) -> Optional[UserType]:
        try:
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if user:
                return UserType(
                    id=str(user["_id"]),
                    name=user["name"],
                    email=user["email"],
                    phone=user["phone"],
                    usertype_id=str(user["usertype_id"]),
                    is_active=user["is_active"],
                    is_deleted=user["is_deleted"],
                    created_at=user["created_at"]
                )
            return None
        except (PyMongoError, ValueError) as e:
            print(f"MongoDB/ValueError Error: {e}")
            return None

# --- GraphQL Mutations ---
@strawberry.type
class Mutation:

    @strawberry.mutation
    def signup(self, input: UserInput) -> UserResponse:
        """Create a new user with a hashed password in MongoDB."""
        try:
            if users_collection.find_one({"email": input.email}):
                return UserResponse(status=409, message=f"User with email '{input.email}' already exists.")

            if users_collection.find_one({"phone": input.phone}):
                return UserResponse(status=409, message=f"User with phone '{input.phone}' already exists.")

            default_usertype = usertypes_collection.find_one({"usertype": "user"})
            if not default_usertype:
                return UserResponse(status=404, message="Default 'user' usertype not found.")

            hashed_password = bcrypt.hashpw(input.password.encode('utf-8'), bcrypt.gensalt())

            new_user_data = UserModel(
                name=input.name,
                email=input.email,
                phone=input.phone,
                password=hashed_password.decode('utf-8'),
                usertype_id=default_usertype["_id"],
                is_active=True,
                is_deleted=False
            )

            user_dict = new_user_data.model_dump(by_alias=True)

            if user_dict.get('_id') is None:
                del user_dict['_id']

            insert_result = users_collection.insert_one(user_dict)

            return UserResponse(
                status=200,
                message="Signup successful",
                data=UserType(
                    id=str(insert_result.inserted_id),
                    name=new_user_data.name,
                    email=new_user_data.email,
                    phone=new_user_data.phone,
                    usertype_id=str(new_user_data.usertype_id),
                    is_active=new_user_data.is_active,
                    is_deleted=new_user_data.is_deleted,
                    created_at=new_user_data.created_at
                )
            )

        except (PyMongoError, ValidationError) as e:
            return UserResponse(status=500, message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    def login(self, email: str, password: str) -> UserResponse:
        """Login a user by verifying their password."""
        try:
            print(f"Attempting to log in with email: {email}")
            user_doc = users_collection.find_one({"email": email, "isDeleted": False})

            print(f"User document found: {user_doc}")

            if user_doc:
                if bcrypt.checkpw(password.encode('utf-8'), user_doc["password"].encode('utf-8')):
                    print(f"User '{user_doc['email']}' logged in successfully.")

                    login_entry_data = LoginModel(user_id=user_doc["_id"])
                    login_dict = login_entry_data.model_dump(by_alias=True)
                    if login_dict.get('_id') is None:
                        del login_dict['_id']
                    logins_collection.insert_one(login_dict)

                    return UserResponse(
                        status=200,
                        message="Login successful",
                        data=UserType(
                            id=str(user_doc["_id"]),
                            name=user_doc["name"],
                            email=user_doc["email"],
                            phone=user_doc["phone"],
                            usertype_id=str(user_doc["usertype_id"]),
                            is_active=user_doc["isActive"],
                            is_deleted=user_doc["isDeleted"],
                            created_at=user_doc["created_at"]
                        )
                    )
                else:
                    return UserResponse(status=401, message="Incorrect email or password.")
            else:
                return UserResponse(status=404, message="User not found or is deleted.")

        except PyMongoError as e:
            return UserResponse(status=500, message=f"Database error: {e}")
        except Exception as e:
            return UserResponse(status=500, message=f"Unexpected error: {e}")

# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
