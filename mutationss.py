
#mongodb code 

# mutations.py
# Libraries to install:
# pip install strawberry-graphql-fastapi bcrypt pymongo "pydantic[email]"

import bcrypt
import strawberry
import base64
import uuid
import os
from PIL import Image
from typing import List, Optional, Union
from datetime import datetime
from bson import ObjectId
from pymongo.errors import PyMongoError
from pydantic import ValidationError
from strawberry.file_uploads import Upload

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

# --- GraphQL Types ---

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
    
    @strawberry.field
    def courses(self) -> List[CourseType]:
        try:
            bundle_doc = package_bundle_collection.find_one({"package_id": self.id})
            if not bundle_doc or not bundle_doc.get("course_ids"):
                return []

            course_object_ids = [ObjectId(cid) for cid in bundle_doc["course_ids"]]
            courses_docs = list(courses_collection.find({"_id": {"$in": course_object_ids}}))
            
            return [
                CourseType(
                    id=str(c["_id"]),
                    title=c.get("title"),
                    description=c.get("description"),
                    thumbnail=c.get("thumbnail"),
                    language=c.get("language"),
                    desktop_available=c.get("desktopAvailable", False),
                    created_by=c.get("created_by"),
                    creation_stage=c.get("creationStage"),
                    publish_status=c.get("publishStatus"),
                    is_deleted=c.get("isDeleted", False),
                    deleted_by=c.get("deletedBy"),
                    deleted_at=c.get("deletedAt"),
                    created_at=c.get("createdAt")
                ) for c in courses_docs
            ]
        except (PyMongoError, ValueError) as e:
            print(f"Error resolving courses for package {self.id}: {e}")
            return []


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

@strawberry.type
class UserResponse:
    status: int
    message: str
    data: Optional[UserType] = None

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
                    updated_by=pkg.get("updatedBy")
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
                from bson import ObjectId
                if ObjectId.is_valid(created_by):
                    creator_or.append({"createdBy": ObjectId(created_by)})
                query_filter["$or"] = creator_or
            else:
                query_filter["isDeleted"] = False

            packages = list(packages_collection.find(query_filter))
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
                    updated_by=pkg.get("updatedBy")
                )
                for pkg in packages
            ]
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []

# --- GraphQL Mutations ---
@strawberry.type
class Mutation:
    @strawberry.mutation
    def signup(self, input: UserInput) -> UserResponse:
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

    @strawberry.mutation
    async def create_package(
        self,
        title: str,
        description: Optional[str] = None,
        banner_file: Optional[Upload] = None,
        theme_file: Optional[Upload] = None,
        created_by: Optional[str] = None
    ) -> PackageResponse:
        try:
            banner_url = None
            theme_url = None

            if banner_file:
                banner_url = await save_and_compress_file(banner_file, "banners")
                print('banner_url:', banner_url)

            if theme_file:
                theme_url = await save_and_compress_file(theme_file, "themes")

            new_package_data = PackageModel(
                title=title,
                description=description,
                bannerUrl=banner_url,
                themeUrl=theme_url,
                createdBy=created_by
            )
            
            package_dict = new_package_data.model_dump(by_alias=True)
            if package_dict.get('_id') is None:
                del package_dict['_id']

            insert_result = packages_collection.insert_one(package_dict)

            return PackageResponse(
                status=200,
                message="Package created successfully.",
                data=PackageDetailsType(
                    id=str(insert_result.inserted_id),
                    title=new_package_data.title,
                    description=new_package_data.description,
                    banner_url=new_package_data.banner_url,
                    theme_url=new_package_data.theme_url,
                    is_active=new_package_data.is_active,
                    is_deleted=new_package_data.is_deleted,
                    created_at=new_package_data.created_at,
                    updated_at=new_package_data.updated_at,
                    created_by=new_package_data.created_by,
                    updated_by=new_package_data.updated_by
                )
            )
        except (PyMongoError, ValidationError) as e:
            if banner_url:
                delete_previous_file(banner_url.lstrip('/'))
            if theme_url:
                delete_previous_file(theme_url.lstrip('/'))
            return PackageResponse(status=500, message=f"An error occurred: {e}")
        except Exception as e:
            if banner_url:
                delete_previous_file(banner_url.lstrip('/'))
            if theme_url:
                delete_previous_file(theme_url.lstrip('/'))
            return PackageResponse(status=500, message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    async def update_package(
        self,
        package_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        banner_file: Optional[Upload] = None,
        theme_file: Optional[Upload] = None,
        updated_by: Optional[str] = None
    ) -> PackageResponse:
        try:
            existing_package_doc = packages_collection.find_one({"_id": ObjectId(package_id)})
            if not existing_package_doc:
                return PackageResponse(status=404, message="Package not found.")

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
            if updated_by is not None:
                update_data["updatedBy"] = updated_by
            
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
                        updated_by=updated_package_doc.get("updatedBy")
                    )
                )
            else:
                return PackageResponse(status=500, message="Failed to update package.")

        except (PyMongoError, ValueError) as e:
            return PackageResponse(status=500, message=f"An error occurred: {e}")
        
    ### To get the all packages of the users
    @strawberry.mutation
    def get_packages(self, created_by: Optional[str] = None) -> List[PackageDetailsType]:
        """
        Fetch packages:
        - If created_by is not provided → only active (isDeleted = False) packages.
        - If created_by is provided → all packages for that user, regardless of isDeleted status.
        """
        try:
            query_filter = {}

            if created_by:
                # Match both string and ObjectId versions
                creator_or = [{"createdBy": created_by}]
                from bson import ObjectId
                if ObjectId.is_valid(created_by):
                    creator_or.append({"createdBy": ObjectId(created_by)})
                query_filter["$or"] = creator_or
            else:
                # Only non-deleted packages if no creator filter
                query_filter["isDeleted"] = False

            packages = list(packages_collection.find(query_filter))
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
                    updated_by=pkg.get("updatedBy")
                )
                for pkg in packages
            ]
        except PyMongoError as e:
            print(f"MongoDB Error: {e}")
            return []

    @strawberry.mutation
    def create_package_bundle(self, input: PackageBundleInput) -> PackageBundleResponse:
        """
        Creates a new package bundle, linking a package to a list of courses.
        """
        try:
            if not packages_collection.find_one({"_id": ObjectId(input.package_id)}):
                return PackageBundleResponse(status=404, message="Parent package not found.")
            
            if package_bundle_collection.find_one({"package_id": input.package_id}):
                return PackageBundleResponse(
                    status=409, 
                    message=f"Bundle for package '{input.package_id}' already exists. Use update_package_bundle instead."
                )

            course_object_ids = [ObjectId(cid) for cid in input.course_ids]
            if len(list(courses_collection.find({"_id": {"$in": course_object_ids}}))) != len(input.course_ids):
                return PackageBundleResponse(status=404, message="One or more course IDs not found.")

            new_bundle_data = PackageBundleModel(
                package_id=input.package_id,
                course_ids=input.course_ids
            )
            
            bundle_dict = new_bundle_data.model_dump(by_alias=True)
            if bundle_dict.get('_id') is None:
                del bundle_dict['_id']

            insert_result = package_bundle_collection.insert_one(bundle_dict)

            courses_docs = list(courses_collection.find({"_id": {"$in": course_object_ids}}))
            resolved_courses = [
                CourseType(
                    id=str(c["_id"]),
                    title=c.get("title"),
                    description=c.get("description"),
                    thumbnail=c.get("thumbnail"),
                    language=c.get("language"),
                    desktop_available=c.get("desktopAvailable", False),
                    created_by=c.get("created_by"),
                    creation_stage=c.get("creationStage"),
                    publish_status=c.get("publishStatus"),
                    is_deleted=c.get("isDeleted"),
                    deleted_by=c.get("deletedBy"),
                    deleted_at=c.get("deletedAt"),
                    created_at=c.get("createdAt")
                ) for c in courses_docs
            ]

            return PackageBundleResponse(
                status=200,
                message="Package bundle created successfully.",
                data=PackageBundleType(
                    id=str(insert_result.inserted_id),
                    package_id=new_bundle_data.package_id,
                    courses=resolved_courses,
                    created_at=new_bundle_data.created_at
                )
            )

        except (PyMongoError, ValueError) as e:
            return PackageBundleResponse(status=500, message=f"An error occurred: {e}")
        except Exception as e:
            return PackageBundleResponse(status=500, message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    def update_package_bundle(self, bundle_id: str, course_ids: List[str]) -> PackageBundleResponse:
        """
        Updates an existing package bundle with a new list of courses.
        """
        try:
            existing_bundle_doc = package_bundle_collection.find_one({"_id": ObjectId(bundle_id)})
            if not existing_bundle_doc:
                return PackageBundleResponse(status=404, message="Package bundle not found.")

            course_object_ids = [ObjectId(cid) for cid in course_ids]
            if len(list(courses_collection.find({"_id": {"$in": course_object_ids}}))) != len(course_ids):
                return PackageBundleResponse(status=404, message="One or more course IDs not found.")
            
            update_result = package_bundle_collection.update_one(
                {"_id": ObjectId(bundle_id)},
                {"$set": {"course_ids": course_ids}}
            )

            if update_result.modified_count == 1:
                updated_bundle_doc = package_bundle_collection.find_one({"_id": ObjectId(bundle_id)})
                
                resolved_courses = [
                    CourseType(
                        id=str(c["_id"]),
                        title=c.get("title"),
                        description=c.get("description"),
                        thumbnail=c.get("thumbnail"),
                        language=c.get("language"),
                        desktop_available=c.get("desktopAvailable", False),
                        created_by=c.get("created_by"),
                        creation_stage=c.get("creationStage"),
                        publish_status=c.get("publishStatus"),
                        is_deleted=c.get("isDeleted"),
                        deleted_by=c.get("deletedBy"),
                        deleted_at=c.get("deletedAt"),
                        created_at=c.get("createdAt")
                    ) for c in courses_collection.find({"_id": {"$in": course_object_ids}})
                ]

                return PackageBundleResponse(
                    status=200,
                    message="Package bundle updated successfully.",
                    data=PackageBundleType(
                        id=str(updated_bundle_doc["_id"]),
                        package_id=updated_bundle_doc["package_id"],
                        courses=resolved_courses,
                        created_at=updated_bundle_doc["created_at"]
                    )
                )
            else:
                return PackageBundleResponse(status=500, message="Failed to update package bundle.")
        except (PyMongoError, ValueError) as e:
            return PackageBundleResponse(status=500, message=f"An error occurred: {e}")

    @strawberry.mutation
    def delete_package_bundle(self, bundle_id: str) -> PackageBundleResponse:
        """Deletes a package bundle by its ID."""
        try:
            delete_result = package_bundle_collection.delete_one({"_id": ObjectId(bundle_id)})
            if delete_result.deleted_count == 1:
                return PackageBundleResponse(status=200, message="Package bundle deleted successfully.")
            else:
                return PackageBundleResponse(status=404, message="Package bundle not found.")
        except (PyMongoError, ValueError) as e:
            return PackageBundleResponse(status=500, message=f"An error occurred: {e}")

# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)