import bcrypt
import strawberry
import base64
import uuid
import os
from PIL import Image
from typing import List, Optional, Union
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo.errors import PyMongoError
from pydantic import ValidationError
from strawberry.file_uploads import Upload
from dotenv import load_dotenv
import jwt
import re

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")

# Import the database connection and Pydantic models
from db import (
    users_collection,
    logins_collection,
    usertypes_collection,
    packages_collection,
    courses_collection,
    package_bundle_collection
)
from models import (
    UserModel,
    LoginModel,
    UserTypeModel,
    PackageModel,
    PackageBundleModel
)

# ----------------- AUTHENTICATION CODE (COMMENTED FOR DEVELOPMENT) -----------------
from authenticate import AuthenticatedUser
# -----------------------------------------------------------------------------------

# --- GraphQL Types ---

@strawberry.type
class UserType:
    id: str = strawberry.field(name="_id")
    name: str
    email: str
    phone: str
    usertype_id: str
    usertype:str
    is_active: bool = strawberry.field(name="isActive")
    is_deleted: bool = strawberry.field(name="isDeleted")
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.type
class UserTypeType:
    id: str = strawberry.field(name="_id")
    usertype: str = strawberry.field(name="usertype")
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.type
class CourseType:
    id: str = strawberry.field(name="_id")
    title: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    language: Optional[str] = None
    desktop_available: bool = strawberry.field(name="desktopAvailable", default=True)
    created_by: Optional[str] = strawberry.field(name="createdBy")
    creation_stage: Optional[str] = strawberry.field(name="creationStage")
    publish_status: Optional[str] = strawberry.field(name="publishStatus")
    is_deleted: bool = strawberry.field(name="isDeleted", default=False)
    deleted_by: Optional[str] = strawberry.field(name="deletedBy")
    deleted_at: Optional[datetime] = strawberry.field(name="deletedAt")
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.type
class PackageBundleType:
    id: str = strawberry.field(name="_id")
    package_id: str
    courses: List[CourseType]
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.type
class PackageDetailsType:
    id: str = strawberry.field(name="_id")
    title: str
    description: Optional[str] = None
    banner_url: Optional[str] = strawberry.field(name="bannerUrl")
    theme_url: Optional[str] = strawberry.field(name="themeUrl")
    is_active: bool = strawberry.field(name="isActive")
    is_deleted: bool = strawberry.field(name="isDeleted")
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")
    created_by: Optional[str] = strawberry.field(name="createdBy")
    updated_by: Optional[str] = strawberry.field(name="updatedBy")
    price: Optional[float] = None
    course_ids: Optional[List[str]] = None  # Add this field
    telegram_id: Optional[List[str]] = None # Updated to List[str]
    
    # @strawberry.field
    # def courses(self) -> List[CourseType]:
    #     try:
    #         bundle_doc = package_bundle_collection.find_one({"package_id": self.id})
    #         if not bundle_doc or not bundle_doc.get("course_ids"):
    #             return []
    #         course_object_ids = [ObjectId(cid) for cid in bundle_doc["course_ids"]]
    #         courses_docs = list(courses_collection.find({"_id": {"$in": course_object_ids}}))
    #         return [
    #             CourseType(
    #                 id=str(c["_id"]),
    #                 title=c.get("title"),
    #                 description=c.get("description"),
    #                 thumbnail=c.get("thumbnail"),
    #                 language=c.get("language"),
    #                 desktop_available=c.get("desktopAvailable", False),
    #                 created_by=c.get("created_by"),
    #                 creation_stage=c.get("creationStage"),
    #                 publish_status=c.get("publishStatus"),
    #                 is_deleted=c.get("isDeleted", False),
    #                 deleted_by=c.get("deletedBy"),
    #                 deleted_at=c.get("deletedAt"),
    #                 created_at=c.get("createdAt")
    #             ) for c in courses_docs
    #         ]
    #     except (PyMongoError, ValueError) as e:
    #         print(f"Error resolving courses for package {self.id}: {e}")
    #         return []


@strawberry.input
class UserInput:
    name: str
    email: str
    phone: str
    password: str

@strawberry.input
class PackageInput:
    title: str
    description: Optional[str] = None
    banner_url: Optional[str] = None
    theme_url: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

@strawberry.input
class PackageBundleInput:
    package_id: str
    course_ids: List[str]
    price: Optional[float] = None

@strawberry.type
class UserResponse:
    status: int
    message: str
    data: Optional[UserType] = None
    token: Optional[str] = None

@strawberry.type
class PackageResponse:
    status: int
    message: str
    data: Optional[PackageDetailsType] = None

@strawberry.type
class PackageBundleResponse:
    status: int
    message: str
    data: Optional[PackageBundleType] = None

# --- Helper Functions for File Handling ---

async def save_and_compress_file(upload: Upload, subfolder: str) -> str:
    """
    Saves an uploaded file to a subfolder, compresses it, and returns its URL.
    """
    extension = upload.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{extension}"
    folder_path = os.path.join("uploads", subfolder)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, filename)

    content = await upload.read()
    with open(file_path, "wb") as f:
        f.write(content)

    image = Image.open(file_path)
    image.save(file_path, optimize=True, quality=60)

    return f"/uploads/{subfolder}/{filename}"

def delete_previous_file(file_path: Optional[str]):
    """
    Deletes a file if the path exists and is not a default or null value.
    """
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

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
    
    @strawberry.field
    def all_packages(self) -> List[PackageDetailsType]:
        try:
            packages = list(packages_collection.find({"is_deleted": False}))
            return [
                PackageDetailsType(
                    id=str(pkg["_id"]),
                    title=pkg["title"],
                    description=pkg.get("description"),
                    banner_url=pkg.get("bannerUrl"),
                    theme_url=pkg.get("themeUrl"),
                    is_active=pkg.get("isActive"),
                    is_deleted=pkg.get("isDeleted"),
                    created_at=pkg["createdAt"],
                    updated_at=pkg["updatedAt"],
                    created_by=pkg.get("createdBy"),
                    updated_by=pkg.get("updatedBy"),
                    price=pkg.get("price", 0.0)
                ) for pkg in packages
            ]
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []

    @strawberry.field
    def get_packages(self, created_by: Optional[str] = None) -> List[PackageDetailsType]:
        try:
            query_filter = {}
            if created_by:
                creator_or = [{"createdBy": created_by}]
                if ObjectId.is_valid(created_by):
                    creator_or.append({"createdBy": ObjectId(created_by)})
                query_filter["$or"] = creator_or
            else:
                query_filter["isDeleted"] = False

            packages = list(packages_collection.find(query_filter))
            
            if not packages:
                return []

            return [
                PackageDetailsType(
                    id=str(pkg["_id"]),
                    title=pkg.get("title", ""),
                    description=pkg.get("description"),
                    banner_url=pkg.get("bannerUrl"),
                    theme_url=pkg.get("themeUrl"),
                    is_active=pkg.get("isActive"),
                    is_deleted=pkg.get("isDeleted"),
                    created_at=pkg.get("createdAt"),
                    updated_at=pkg.get("updatedAt"),
                    created_by=pkg.get("createdBy"),
                    updated_by=pkg.get("updatedBy"),
                    price=pkg.get("price", 0.0),
                    course_ids=pkg.get("course_ids", []),
                    telegram_id=[pkg.get("telegram_id")] if isinstance(pkg.get("telegram_id"), str) else pkg.get("telegram_id", []),
                )
                for pkg in packages
            ]
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return []

# --- GraphQL Mutations ---
@strawberry.type
class Mutation:
    @strawberry.mutation
    def signup(self, input: UserInput) -> UserResponse:
        try:
            # ----------------- VALIDATION CHECKS -----------------
            # Phone number validation (exactly 10 digits)
            if not input.phone.isdigit() or len(input.phone) != 10:
                return UserResponse(status=400, message="Phone number must be exactly 10 digits.")

            # Email format validation
            if not re.match(r"[^@]+@[^@]+\.[^@]+", input.email):
                return UserResponse(status=400, message="Invalid email format.")

            # Password complexity validation
            if len(input.password) < 8 or not any(c.isupper() for c in input.password) or not any(c.islower() for c in input.password) or not any(c.isdigit() for c in input.password):
                return UserResponse(status=400, message="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one digit.")
            # -----------------------------------------------------
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
            new_user_id = insert_result.inserted_id
            payload = {
                "id": str(new_user_id),
                "name": new_user_data.name,
                "email": new_user_data.email,
                "phone":new_user_data.phone,
                "usertype": "user",
                "jti": str(uuid.uuid4())
            }
            token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
            login_entry_data = LoginModel(user_id=new_user_id, token=token)
            logins_collection.insert_one(login_entry_data.model_dump(by_alias=True, exclude_none=True))
            return UserResponse(
                status=200,
                message="Signup successful",
                data=UserType(
                    id=str(new_user_id),
                    name=new_user_data.name,
                    email=new_user_data.email,
                    phone=new_user_data.phone,
                    usertype_id=str(new_user_data.usertype_id),
                    usertype="user",
                    is_active=new_user_data.is_active,
                    is_deleted=new_user_data.is_deleted,
                    created_at=new_user_data.created_at
                ),
                token=token
            )
        except (PyMongoError, ValidationError) as e:
            return UserResponse(status=500, message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    def login(self, email: str, password: str) -> UserResponse:
        try:
            print(f"Attempting to log in with email: {email}")
            user_doc = users_collection.find_one({"email": email, "isDeleted": False})
            if not user_doc:
                return UserResponse(status=404, message="User not found or is deleted.")
            if not bcrypt.checkpw(password.encode('utf-8'), user_doc["password"].encode('utf-8')):
                return UserResponse(status=401, message="Incorrect email or password.")
            usertype_doc = usertypes_collection.find_one({"_id": ObjectId(user_doc["usertype_id"])})
            print(f"User document found: {user_doc}")
            print(f"User '{user_doc['email']}' logged in successfully.")
            payload = {
                "id": str(user_doc["_id"]),
                "name": user_doc["name"],
                "email": user_doc["email"],
                "phone": user_doc["phone"],
                "usertype": usertype_doc["usertype"] if usertype_doc else None,
                "jti": str(uuid.uuid4())
            }
            token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
            logins_collection.update_one(
                {"user_id": user_doc["_id"]},
                {"$set": {"token": token, "created_at": datetime.utcnow()}},
                upsert=True
            )
            return UserResponse(
                status=200,
                message="Login successful",
                data=UserType(
                    id=str(user_doc["_id"]),
                    name=user_doc["name"],
                    email=user_doc["email"],
                    phone=user_doc["phone"],
                    usertype_id=str(user_doc["usertype_id"]),
                    usertype=usertype_doc["usertype"] if usertype_doc else None,
                    is_active=user_doc.get("is_active", True),
                    is_deleted=user_doc.get("is_deleted", False),
                    created_at=user_doc["created_at"]
                ),
                token=token
            )
        except PyMongoError as e:
            return UserResponse(status=500, message=f"Database error: {e}")
        except Exception as e:
            return UserResponse(status=500, message=f"Unexpected error: {e}")



    @strawberry.mutation
    async def create_package(
        self,
        info: strawberry.Info,
        title: str,
        description: str,
        banner_file: Upload,
        theme_file: Upload,
        price: float,
        course_ids: Optional[List[str]] = None,   # Made Optional
        telegram_id: Optional[List[str]] = None   # Already Optional
    ) -> PackageResponse:
        try:
            # ----------------- AUTHENTICATION CHECK (COMMENTED FOR DEVELOPMENT) -----------------
            current_user: Optional[AuthenticatedUser] = info.context.get("current_user")
            if not current_user:
                return PackageResponse(status=401, message="Authentication required: You must be logged in.")
            created_by_id = current_user.id
            # ------------------------------------------------------------------------------------

            # ----------------- DEVELOPMENT PLACEHOLDER (UNCOMMENTED) -----------------
            # created_by_id = "development_user"
            # -------------------------------------------------------------------------

            # Check if a package with the same title already exists
            if packages_collection.find_one({"title": title, "isDeleted": False}):
                return PackageResponse(status=409, message=f"Package with title '{title}' already exists.")

            banner_url = None
            theme_url = None

            # Save files
            banner_url = await save_and_compress_file(banner_file, "banners")
            theme_url = await save_and_compress_file(theme_file, "themes")

            # Validate at least one of course_ids or telegram_id is provided
            if not course_ids and not telegram_id:
                return PackageResponse(status=400, message="Either course_ids or telegram_id must be provided.")

            # Validate course IDs (only if provided)
            if course_ids:
                course_object_ids = [ObjectId(cid) for cid in course_ids]
                if len(list(courses_collection.find({"_id": {"$in": course_object_ids}}))) != len(course_ids):
                    return PackageResponse(status=404, message="One or more course IDs not found.")

            # Create new package data
            new_package_data = PackageModel(
                title=title,
                description=description,
                bannerUrl=banner_url,
                themeUrl=theme_url,
                createdBy=created_by_id,
                course_ids=course_ids if course_ids else [],
                price=price,
                telegram_id=telegram_id if telegram_id else []
            )

            package_dict = new_package_data.model_dump(by_alias=True)
            if package_dict.get('_id') is None:
                del package_dict['_id']

            insert_result = packages_collection.insert_one(package_dict)

            # Fetch the newly created package to ensure accurate response data
            new_package_doc = packages_collection.find_one({"_id": insert_result.inserted_id})

            return PackageResponse(
                status=200,
                message="Package created successfully.",
                data=PackageDetailsType(
                    id=str(new_package_doc["_id"]),
                    title=new_package_doc.get("title"),
                    description=new_package_doc.get("description"),
                    banner_url=new_package_doc.get("bannerUrl"),
                    theme_url=new_package_doc.get("themeUrl"),
                    is_active=new_package_doc.get("isActive"),
                    is_deleted=new_package_doc.get("isDeleted"),
                    created_at=new_package_doc.get("createdAt"),
                    updated_at=new_package_doc.get("updatedAt"),
                    created_by=new_package_doc.get("createdBy"),
                    updated_by=new_package_doc.get("updatedBy"),
                    course_ids=new_package_doc.get("course_ids", []),
                    price=new_package_doc.get("price", 0.0),
                    telegram_id=new_package_doc.get("telegram_id", [])
                )
            )
        except (PyMongoError, ValidationError) as e:
            if banner_url:
                delete_previous_file(banner_url.lstrip('/'))
            if theme_url:
                delete_previous_file(theme_url.lstrip('/'))
            return PackageResponse(status=500, message=f"An error occurred: {e}")
        except Exception as e:
            if 'created_by_id' in locals() and banner_url:
                delete_previous_file(banner_url.lstrip('/'))
            if 'created_by_id' in locals() and theme_url:
                delete_previous_file(theme_url.lstrip('/'))
            return PackageResponse(status=500, message=f"An unexpected error occurred: {e}")




    @strawberry.mutation
    async def update_package(
        self,
        info: strawberry.Info,
        package_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        banner_file: Optional[Upload] = None,
        theme_file: Optional[Upload] = None,
        course_ids: Optional[List[str]] = None,
        price: Optional[float] = None,
        telegram_id: Optional[List[str]] = None # Updated to List[str]
    ) -> PackageResponse:
        try:
            # ----------------- AUTHENTICATION CHECK (COMMENTED FOR DEVELOPMENT) -----------------
            current_user: Optional[AuthenticatedUser] = info.context.get("current_user")
            if not current_user:
                return PackageResponse(status=401, message="Authentication required: You must be logged in.")
            # ------------------------------------------------------------------------------------

            existing_package_doc = packages_collection.find_one({"_id": ObjectId(package_id)})
            if not existing_package_doc:
                return PackageResponse(status=404, message="Package not found.")
            
            # ----------------- OWNERSHIP CHECK (COMMENTED FOR DEVELOPMENT) -----------------
            # if str(existing_package_doc.get("createdBy")) != current_user.id:
            #     raise Exception("Unauthorized: You do not have permission to update this package.")
            updated_by_id = current_user.id
            # -------------------------------------------------------------------------------

            # ----------------- DEVELOPMENT PLACEHOLDER (UNCOMMENTED) -----------------
            # updated_by_id = "development_user"
            # -----------------------------------------------------------------------------

            update_data = {}
            current_banner_url = existing_package_doc.get("bannerUrl")
            current_theme_url = existing_package_doc.get("themeUrl")

            if banner_file:
                if current_banner_url:
                    delete_previous_file(current_banner_url.lstrip('/'))
                update_data["bannerUrl"] = await save_and_compress_file(banner_file, "banners")
            else:
                update_data["bannerUrl"] = current_banner_url

            if theme_file:
                if current_theme_url:
                    delete_previous_file(current_theme_url.lstrip('/'))
                update_data["themeUrl"] = await save_and_compress_file(theme_file, "themes")
            else:
                update_data["themeUrl"] = current_theme_url

            if title is not None:
                update_data["title"] = title
            if description is not None:
                update_data["description"] = description
            if course_ids is not None:
                # Validate course IDs before updating
                course_object_ids = [ObjectId(cid) for cid in course_ids]
                if len(list(courses_collection.find({"_id": {"$in": course_object_ids}}))) != len(course_ids):
                    return PackageResponse(status=404, message="One or more course IDs not found.")
                update_data["course_ids"] = course_ids
            if price is not None:
                update_data["price"] = price
            if telegram_id is not None:
                update_data["telegram_id"] = telegram_id
            
            update_data["updatedBy"] = updated_by_id
            update_data["updatedAt"] = datetime.utcnow()

            update_result = packages_collection.update_one(
                {"_id": ObjectId(package_id)},
                {"$set": update_data}
            )

            if update_result.modified_count == 1:
                updated_package_doc = packages_collection.find_one({"_id": ObjectId(package_id)})
                return PackageResponse(
                    status=200,
                    message="Package updated successfully.",
                    data=PackageDetailsType(
                        id=str(updated_package_doc["_id"]),
                        title=updated_package_doc.get("title"),
                        description=updated_package_doc.get("description"),
                        banner_url=updated_package_doc.get("bannerUrl"),
                        theme_url=updated_package_doc.get("themeUrl"),
                        is_active=updated_package_doc.get("isActive"),
                        is_deleted=updated_package_doc.get("isDeleted"),
                        created_at=updated_package_doc.get("createdAt"),
                        updated_at=updated_package_doc.get("updatedAt"),
                        created_by=updated_package_doc.get("createdBy"),
                        updated_by=updated_package_doc.get("updatedBy"),
                        course_ids=updated_package_doc.get("course_ids"),
                        price=updated_package_doc.get("price", 0.0),
                        telegram_id=updated_package_doc.get("telegram_id")
                    )
                )
            else:
                return PackageResponse(status=500, message="Failed to update package.")
        except (PyMongoError, ValueError) as e:
            return PackageResponse(status=500, message=f"An error occurred: {e}")
        except Exception as e:
            return PackageResponse(status=500, message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    async def delete_package(
        self,
        info: strawberry.Info,
        package_id: str
    ) -> PackageResponse:
        try:
            # ----------------- AUTHENTICATION CHECK -----------------
            # For development, you can use the commented out code
            # deleted_by_id = "development_user"
            current_user: Optional[AuthenticatedUser] = info.context.get("current_user")
            if not current_user:
                return PackageResponse(status=401, message="Authentication required: You must be logged in.")
            deleted_by_id = current_user.id
            # --------------------------------------------------------

            existing_package_doc = packages_collection.find_one({"_id": ObjectId(package_id)})
            if not existing_package_doc:
                return PackageResponse(status=404, message="Package not found.")
            
            # ----------------- OWNERSHIP CHECK -----------------
            # if str(existing_package_doc.get("createdBy")) != current_user.id:
            #     raise Exception("Unauthorized: You do not have permission to delete this package.")
            # ---------------------------------------------------

            update_result = packages_collection.update_one(
                {"_id": ObjectId(package_id)},
                {"$set": {
                    "isDeleted": True,
                    "updatedAt": datetime.utcnow(),
                    "updatedBy": deleted_by_id,
                    "deletedAt": datetime.utcnow(), # Also good to add this
                    "deletedBy": deleted_by_id # And this
                }}
            )

            if update_result.modified_count == 1:
                updated_package_doc = packages_collection.find_one({"_id": ObjectId(package_id)})
                return PackageResponse(
                    status=200,
                    message="Package deleted successfully.",
                    data=PackageDetailsType(
                        id=str(updated_package_doc["_id"]),
                        title=updated_package_doc.get("title"),
                        description=updated_package_doc.get("description"),
                        banner_url=updated_package_doc.get("bannerUrl"),
                        theme_url=updated_package_doc.get("themeUrl"),
                        is_active=updated_package_doc.get("isActive"),
                        is_deleted=updated_package_doc.get("isDeleted"),
                        created_at=updated_package_doc.get("createdAt"),
                        updated_at=updated_package_doc.get("updatedAt"),
                        created_by=updated_package_doc.get("createdBy"),
                        updated_by=updated_package_doc.get("updatedBy"),
                        course_ids=updated_package_doc.get("course_ids"),
                        price=updated_package_doc.get("price", 0.0),
                        telegram_id=updated_package_doc.get("telegram_id", [])
                    )
                )
            else:
                return PackageResponse(status=500, message="Failed to delete package.")
        except (PyMongoError, ValueError) as e:
            return PackageResponse(status=500, message=f"An error occurred: {e}")
        except Exception as e:
            return PackageResponse(status=500, message=f"An unexpected error occurred: {e}")


# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)