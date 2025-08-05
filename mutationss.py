
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
    # Change 'name' to 'usertype' to match your MongoDB field if you don't rename it
    usertype: str = strawberry.field(name="usertype") # Assuming your field is 'usertype'
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

@strawberry.type
class UserError:
    message: str

@strawberry.input
class UserInput:
    name: str
    email: str
    phone: str
    password: str

# --- GraphQL Queries ---
@strawberry.type
class Query:
    @strawberry.field
    def all_users(self) -> List[UserType]:
        """Fetch all active users from the MongoDB 'users' collection."""
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
        """Fetch all user types."""
        try:
            usertypes = list(usertypes_collection.find())
            return [
                UserTypeType(
                    id=str(ut["_id"]),
                    usertype=ut["usertype"], # Changed from ut["name"] to ut["usertype"]
                    created_at=ut["createdAt"]
                ) for ut in usertypes
            ]
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []
            
    @strawberry.field
    def user(self, user_id: str) -> Optional[UserType]:
        """Fetch a single user by ID."""
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
    def signup(self, input: UserInput) -> Union[UserType, UserError]:
        """Create a new user with a hashed password in MongoDB."""
        try:
            # Check if user with the given email already exists
            existing_user_by_email = users_collection.find_one({"email": input.email})
            if existing_user_by_email:
                return UserError(message=f"User with email '{input.email}' already exists.")

            # Check if user with the given phone number already exists
            existing_user_by_phone = users_collection.find_one({"phone": input.phone})
            if existing_user_by_phone:
                return UserError(message=f"User with phone '{input.phone}' already exists.")

            # Get the default usertype_id by searching for 'usertype: "user"'
            default_usertype = usertypes_collection.find_one({"usertype": "user"}) # Changed from "name" to "usertype"
            if not default_usertype:
                return UserError(message="Default 'user' usertype not found. Please create it first.")

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
            
            # Convert Pydantic model to dictionary
            user_dict = new_user_data.model_dump(by_alias=True)
            
            # --- CRITICAL FIX: Explicitly remove '_id' if it's None ---
            if user_dict.get('_id') is None:
                del user_dict['_id']
            # --- END CRITICAL FIX ---

            # --- DEBUGGING PRINT STATEMENT ---
            print("Data being sent to MongoDB:", user_dict)
            # --- END DEBUGGING ---

            insert_result = users_collection.insert_one(user_dict)
            
            # The constructor of UserType expects 'id' and 'usertype_id' as strings
            return UserType(
                id=str(insert_result.inserted_id),
                name=new_user_data.name,
                email=new_user_data.email,
                phone=new_user_data.phone,
                usertype_id=str(new_user_data.usertype_id),
                is_active=new_user_data.is_active,
                is_deleted=new_user_data.is_deleted,
                created_at=new_user_data.created_at
            )
        except (PyMongoError, ValidationError) as e:
            print(f"Error during signup: {e}")
            return UserError(message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    def login(self, email: str, password: str) -> Union[UserType, UserError]:
        """Login a user by verifying their password against MongoDB."""
        try:
            # --- DEBUGGING: Print the email being searched ---
            print(f"Attempting to log in with email: {email}")
            # Corrected: Query for 'isDeleted' to match MongoDB document field name
            user_doc = users_collection.find_one({"email": email, "isDeleted": False}) 

            # --- DEBUGGING: Print the user document found (or None) ---
            print(f"User document found: {user_doc}")

            if user_doc:
                # --- DEBUGGING: Print passwords for comparison ---
                print(f"Provided password: {password}")
                print(f"Stored hashed password: {user_doc.get('password')}")

                if bcrypt.checkpw(password.encode('utf-8'), user_doc["password"].encode('utf-8')):
                    print(f"User '{user_doc['email']}' logged in successfully.")
                    
                    # Create a login entry in the database
                    login_entry_data = LoginModel(user_id=user_doc["_id"])
                    
                    # Convert Pydantic model to dictionary
                    login_dict = login_entry_data.model_dump(by_alias=True)
                    
                    # --- CRITICAL FIX: Explicitly remove '_id' if it's None ---
                    if login_dict.get('_id') is None:
                        del login_dict['_id']
                    # --- END CRITICAL FIX ---

                    logins_collection.insert_one(login_dict)

                    return UserType(
                        id=str(user_doc["_id"]),
                        name=user_doc["name"],
                        email=user_doc["email"],
                        phone=user_doc["phone"],
                        usertype_id=str(user_doc["usertype_id"]),
                        is_active=user_doc["isActive"], # Changed from 'is_active' to 'isActive'
                        is_deleted=user_doc["isDeleted"], # Changed from 'is_deleted' to 'isDeleted'
                        created_at=user_doc["created_at"]
                    )
                else:
                    print("Password mismatch detected.")
                    return UserError(message="Incorrect email or password.")
            else:
                print("User not found or is deleted.")
                return UserError(message="Incorrect email or password.")
        except PyMongoError as e:
            print(f"Error during login: {e}")
            return UserError(message=f"An unexpected error occurred: {e}")
        except Exception as e: # Catch any other unexpected errors
            print(f"An unexpected error occurred during login: {e}")
            return UserError(message=f"An unexpected error occurred: {e}")

schema = strawberry.Schema(query=Query, mutation=Mutation)
