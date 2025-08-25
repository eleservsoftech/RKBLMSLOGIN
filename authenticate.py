import os
from dotenv import load_dotenv
import jwt
from bson import ObjectId
from typing import Optional
import strawberry
from fastapi import Request

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")

# Import your database collections here
from db import logins_collection

# This class defines the type of the user object that will be returned
@strawberry.type
class AuthenticatedUser:
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    usertype: Optional[str] = None

# This is the dependency resolver function. It takes a FastAPI Request.
def get_current_user(request: Request) -> AuthenticatedUser:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise Exception("Authentication required: Authorization header is missing or malformed.")
    
    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token. Please log in again.")
    except Exception as e:
        raise Exception(f"Failed to decode token: {e}")

    user_id_from_token = payload.get("id")
    if not user_id_from_token:
        raise Exception("Invalid token payload: User ID is missing.")
    
    # Database check to ensure the token is not revoked
    try:
        db_token_doc = logins_collection.find_one({"user_id": ObjectId(user_id_from_token), "token": token})
        
        if not db_token_doc:
            raise Exception("Invalid or revoked token. Please log in again.")
    except Exception as e:
        raise Exception(f"Database check failed during authentication: {e}")

    return AuthenticatedUser(
        id=payload["id"],
        name=payload["name"],
        email=payload["email"],
        phone=payload.get("phone"),
        usertype=payload.get("usertype")
    )






