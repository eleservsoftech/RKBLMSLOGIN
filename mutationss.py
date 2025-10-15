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
import logging
from logging.handlers import TimedRotatingFileHandler

# Set up logging with daily rotation
logger = logging.getLogger('MutationsLogger')
logger.setLevel(logging.INFO)
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
handler = TimedRotatingFileHandler(os.path.join(log_dir, 'mutationss.log'), when='midnight', interval=1, backupCount=30)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")

# Import the database connection and Pydantic models
from db import (
    users_collection,
    logins_collection,
    usertypes_collection,
    packages_collection,
    courses_collection,
    purchased_collection,
   
)
# ... (existing imports)
from models import (
    UserModel,
    LoginModel,
    UserTypeModel,
    PackageModel,
    PriceModel,
    FaqModel # NEW: Import FaqModel from your models file
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

# --- UPDATED: CourseDetailsType based on your provided schema ---
@strawberry.type
class CourseDetailsType:
    id: str = strawberry.field(name="_id")
    title: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    hls: Optional[str] = None
    language: Optional[str] = None
    desktop_available: bool = strawberry.field(name="desktopAvailable", default=True)
    created_by: Optional[str] = strawberry.field(name="createdBy")
    creation_stage: Optional[str] = strawberry.field(name="creationStage")
    publish_status: Optional[str] = strawberry.field(name="publishStatus")
    is_deleted: bool = strawberry.field(name="isDeleted", default=False)
    deleted_by: Optional[str] = strawberry.field(name="deletedBy")
    deleted_at: Optional[datetime] = strawberry.field(name="deletedAt")
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.input
class FaqInput:
    question: str
    answer: str

@strawberry.type
class FaqType:
    question: str
    answer: str

@strawberry.type
class PackageBundleType:
    id: str = strawberry.field(name="_id")
    package_id: str
    courses: List[CourseDetailsType]
    created_at: datetime = strawberry.field(name="createdAt")

@strawberry.type
class PackageDetailsType:
    id: str = strawberry.field(name="_id")
    title: str
    description: Optional[str] = None
    banner_url: Optional[str] = strawberry.field(name="bannerUrl")
    theme_url: Optional[str] = strawberry.field(name="themeUrl")
    banner_base64: Optional[str] = None
    theme_base64: Optional[str] = None
    is_active: bool = strawberry.field(name="isActive")
    is_deleted: bool = strawberry.field(name="isDeleted")
    is_draft: bool = strawberry.field(name="isDraft")
    status: Optional[str] = None  # New field to represent the package status
    created_at: datetime = strawberry.field(name="createdAt")
    updated_at: datetime = strawberry.field(name="updatedAt")
    created_by: Optional[str] = strawberry.field(name="createdBy")
    updated_by: Optional[str] = strawberry.field(name="updatedBy")
    deleted_at: Optional[datetime] = strawberry.field(name="deletedAt")
    deleted_by: Optional[str] = strawberry.field(name="deletedBy")
    # price: Optional[float] = None  # REMOVED: This is no longer used
    
    # NEW: The list of price details for different periods
    price_details: Optional[List['PriceType']] = None
    
    course_ids: Optional[List[str]] = None
    # NEW: Return a list of the full course objects
    course_details: Optional[List[CourseDetailsType]] = None
    telegram_id: Optional[List[str]] = None
    faqs: Optional[List['FaqType']] = None
    

    
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


@strawberry.input
class PriceInput:
    period: str  # e.g., "6 months", "1 year"
    actual_price: float
    price: float
    gst: float
    totalprice:float

@strawberry.type
class PriceType:
    period: str
    actual_price: float = strawberry.field(name="actualPrice")
    price: float
    gst: float
    totalprice:float

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

@strawberry.type
class PurchasedCourse:
    course_id: str
    course_view_percent: float
    certificate_sent: bool

@strawberry.type
class PurchaseData:
    purchase_id: str
    user_id: str
    name: str
    email: str
    phone: str
    package_id: Optional[str]
    courses: List[PurchasedCourse]
    created_at: datetime
    updated_at: datetime

@strawberry.input
class CourseProgressInput:
    course_id: str
    course_view_percent: float

# Helper function to fetch course details
async def get_course_details_by_ids(course_ids: List[str]) -> List[dict]:
    """Fetches course documents from the database based on a list of string IDs."""
    logger.info(f"Entering get_course_details_by_ids with course_ids: {course_ids}")
    if not course_ids:
        logger.info("get_course_details_by_ids: No course IDs provided, returning empty list")
        return []
    try:
        course_object_ids = [ObjectId(cid) for cid in course_ids if ObjectId.is_valid(cid)]
        courses_cursor = courses_collection.find({"_id": {"$in": course_object_ids}})
        found_courses = await courses_cursor.to_list(length=None)
        logger.info(f"get_course_details_by_ids: Successfully fetched {len(found_courses)} courses")
        return found_courses
    except Exception as e:
        logger.error(f"get_course_details_by_ids: Error fetching course details: {str(e)}")
        print(f"Error fetching course details: {e}")
        return []

# --- Helper Functions for File Handling ---

async def save_and_compress_file(upload: Upload, subfolder: str) -> str:
    """
    Saves an uploaded file to a subfolder, compresses it, and returns its URL.
    """
    logger.info(f"Entering save_and_compress_file with filename: {upload.filename}, subfolder: {subfolder}")
    extension = upload.filename.split(".")[-1]
    # print('extension:',extension)
    filename = f"{uuid.uuid4()}.{extension}"
    folder_path = os.path.join("uploads", subfolder)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, filename)

    content = await upload.read()
    with open(file_path, "wb") as f:
        f.write(content)

    image = Image.open(file_path)
    image.save(file_path, optimize=True, quality=60)

    result = f"/uploads/{subfolder}/{filename}"
    # print('result:',result)
    logger.info(f"save_and_compress_file: File saved successfully at {result}")
    return result

async def delete_previous_file(file_path: Optional[str]):
    """
    Deletes a file if the path exists and is not a default or null value.
    """
    logger.info(f"Entering delete_previous_file with file_path: {file_path}")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"delete_previous_file: File deleted at {file_path}")
    else:
        logger.info(f"delete_previous_file: No file deleted, path {file_path} does not exist or is None")

# --- GraphQL Queries ---
@strawberry.type
class Query:
    @strawberry.field
    def all_users(self) -> List[UserType]:
        logger.info("Entering all_users query")
        try:
            users = list(users_collection.find({"is_deleted": False}))
            result = [
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
            logger.info(f"all_users: Successfully fetched {len(result)} users")
            return result
        except PyMongoError as e:
            logger.error(f"all_users: MongoDB Error: {str(e)}")
            print(f"MongoDB Error: {e}")
            return []

    @strawberry.field
    def all_user_types(self) -> List[UserTypeType]:
        logger.info("Entering all_user_types query")
        try:
            usertypes = list(usertypes_collection.find())
            result = [
                UserTypeType(
                    id=str(ut["_id"]),
                    usertype=ut["usertype"],
                    created_at=ut["createdAt"]
                ) for ut in usertypes
            ]
            logger.info(f"all_user_types: Successfully fetched {len(result)} user types")
            return result
        except PyMongoError as e:
            logger.error(f"all_user_types: MongoDB Error: {str(e)}")
            print(f"MongoDB Error: {e}")
            return []

    @strawberry.field
    def user(self, user_id: str) -> Optional[UserType]:
        logger.info(f"Entering user query with user_id: {user_id}")
        try:
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if user:
                result = UserType(
                    id=str(user["_id"]),
                    name=user["name"],
                    email=user["email"],
                    phone=user["phone"],
                    usertype_id=str(user["usertype_id"]),
                    is_active=user["is_active"],
                    is_deleted=user["is_deleted"],
                    created_at=user["created_at"]
                )
                logger.info(f"user: Successfully fetched user with id {user_id}")
                return result
            logger.info(f"user: No user found with id {user_id}")
            return None
        except (PyMongoError, ValueError) as e:
            logger.error(f"user: MongoDB/ValueError Error: {str(e)}")
            print(f"MongoDB/ValueError Error: {e}")
            return None
    
    @strawberry.field
    def all_packages(self) -> List[PackageDetailsType]:
        logger.info("Entering all_packages query")
        try:
            packages = list(packages_collection.find({"is_deleted": False}))
            result = [
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
            logger.info(f"all_packages: Successfully fetched {len(result)} packages")
            return result
        except PyMongoError as e:
            logger.error(f"all_packages: MongoDB Error: {str(e)}")
            print(f"MongoDB Error: {e}")
            return []

    # @strawberry.field
    # async def get_packages(self, created_by: Optional[str] = None) -> List[PackageDetailsType]:
    #     """Retrieves a list of packages, optionally filtered by the creator."""
    #     logger.info(f"Entering get_packages with created_by: {created_by}")
    #     try:
    #         query_filter = {}
    #         if created_by:
    #             creator_or = [{"createdBy": created_by}]
    #             if ObjectId.is_valid(created_by):
    #                 creator_or.append({"createdBy": ObjectId(created_by)})
    #             query_filter["$or"] = creator_or
    #         else:
    #             query_filter["isDeleted"] = False

    #         # CORRECTED: Added 'await' to get the list of packages
    #         packages_cursor = packages_collection.find(query_filter)
    #         packages = await packages_cursor.to_list(length=None)

    #         if not packages:
    #             logger.info("get_packages: No packages found")
    #             return []

    #         result_packages = []
    #         for pkg in packages:
    #             # --- 1. Fetch Course Details ---
    #             course_details_list = []
    #             if pkg.get("course_ids"):
    #                 found_courses_data = await get_course_details_by_ids(pkg["course_ids"])
    #                 print('found_courses_data')
    #                 print(found_courses_data)
    #                 # Map the raw data to the CourseDetailsType for the response
    #                 course_details_list = [
    #                     CourseDetailsType(
    #                         id=str(course["_id"]),
    #                         title=course.get("title", ""),
    #                         description=course.get("description"),
    #                         thumbnail=course.get("thumbnail"),
    #                         hls=course.get("hls"),
    #                         language=course.get("language"),
    #                         desktop_available=course.get("desktopAvailable"),
    #                         created_by=str(course.get("createdBy")) if course.get("createdBy") else None,
    #                         creation_stage=course.get("creationStage"),
    #                         publish_status=course.get("publishStatus"),
    #                         is_deleted=course.get("isDeleted"),
    #                         deleted_by=course.get("deletedBy"),
    #                         deleted_at=course.get("deletedAt"),
    #                         created_at=course.get("createdAt")
    #                     )
    #                     for course in found_courses_data
    #                 ]

    #             # --- 2. Convert Banner to Base64 ---
    #             banner_base64_data = None
    #             if pkg.get("bannerUrl"):
    #                 # CORRECTED: Added "static" back to the path
    #                 file_path = os.path.normpath(os.path.join(pkg["bannerUrl"].lstrip('/')))
    #                 try:
    #                     with open(file_path, "rb") as image_file:
    #                         banner_base64_data = base64.b64encode(image_file.read()).decode('utf-8')
    #                 except FileNotFoundError:
    #                     logger.warning(f"get_packages: Banner file not found at {file_path}")
    #                     print(f"Warning: Banner file not found at {file_path}")
    #                 except Exception as e:
    #                     logger.error(f"get_packages: Error reading banner file: {str(e)}")
    #                     print(f"Error reading banner file: {e}")
                
    #             # --- 3. Convert Theme to Base64 ---
    #             theme_base64_data = None
    #             if pkg.get("themeUrl"):
    #                 # CORRECTED: Added "static" back to the path
    #                 file_path = os.path.normpath(os.path.join(pkg["themeUrl"].lstrip('/')))
    #                 try:
    #                     with open(file_path, "rb") as image_file:
    #                         theme_base64_data = base64.b64encode(image_file.read()).decode('utf-8')
    #                 except FileNotFoundError:
    #                     logger.warning(f"get_packages: Theme file not found at {file_path}")
    #                     print(f"Warning: Theme file not found at {file_path}")
    #                 except Exception as e:
    #                     logger.error(f"get_packages: Error reading theme file: {str(e)}")
    #                     print(f"Error reading theme file: {e}")

    #             # --- 4. Format FAQs ---
    #             response_faqs = []
    #             if pkg.get("faqs"):
    #                 response_faqs = [
    #                     FaqType(question=f.get('question'), answer=f.get('answer'))
    #                     for f in pkg.get("faqs", [])
    #                 ]

    #             # Create the response object with all fields, including the new ones
    #             package_response = PackageDetailsType(
    #                 id=str(pkg["_id"]),
    #                 title=pkg.get("title", ""),
    #                 description=pkg.get("description"),
    #                 banner_url=pkg.get("bannerUrl"),
    #                 theme_url=pkg.get("themeUrl"),
    #                 banner_base64=banner_base64_data,  # Now returns the Base64 data
    #                 theme_base64=theme_base64_data, # New: Returns the Base64 data for the theme
    #                 is_active=pkg.get("isActive"),
    #                 is_deleted=pkg.get("isDeleted"),
    #                 is_draft=pkg.get("isDraft"),
    #                 created_at=pkg.get("createdAt"),
    #                 updated_at=pkg.get("updatedAt"),
    #                 created_by=pkg.get("createdBy"),
    #                 updated_by=pkg.get("updatedBy"),
    #                 price=pkg.get("price", 0.0),
    #                 course_ids=pkg.get("course_ids", []),
    #                 course_details=course_details_list,  # New: Returns full course objects
    #                 telegram_id=pkg.get("telegram_id", []),
    #                 faqs=response_faqs,
    #                 deleted_at=None,
    #                 deleted_by=None,
    #             )
    #             result_packages.append(package_response)

    #         logger.info(f"get_packages: Successfully fetched {len(result_packages)} packages")
    #         return result_packages
        
    #     except Exception as e:
    #         logger.error(f"get_packages: An unexpected error occurred: {str(e)}")
    #         print(f"An unexpected error occurred in get_packages: {e}")
    #         return []

    @strawberry.field
    async def get_packages(
        self, created_by: Optional[str] = None, package_id: Optional[str] = None
    ) -> List[PackageDetailsType]:
        """Retrieves a list of packages, optionally filtered by the creator or a specific package ID."""
        logger.info(f"Entering get_packages with created_by: {created_by}, package_id: {package_id}")
        try:
            query_filter = {}
            
            # --- 1. Filter by package_id ---
            if package_id:
                if ObjectId.is_valid(package_id):
                    query_filter["_id"] = ObjectId(package_id)
                else:
                    logger.warning(f"get_packages: Invalid package_id provided: {package_id}")
                    return []
            
            # --- 2. Filter by created_by ---
            elif created_by:
                creator_or = [{"createdBy": created_by}]
                if ObjectId.is_valid(created_by):
                    creator_or.append({"createdBy": ObjectId(created_by)})
                query_filter["$or"] = creator_or
            else:
                query_filter["isDeleted"] = False

            packages_cursor = packages_collection.find(query_filter)
            packages = await packages_cursor.to_list(length=None)

            if not packages:
                logger.info("get_packages: No packages found")
                return []

            result_packages = []
            for pkg in packages:
                # --- Fetch Course Details ---
                course_details_list = []
                if pkg.get("course_ids"):
                    found_courses_data = await get_course_details_by_ids(pkg["course_ids"])
                    course_details_list = [
                        CourseDetailsType(
                            id=str(course["_id"]),
                            title=course.get("title", ""),
                            description=course.get("description"),
                            thumbnail=course.get("thumbnail"),
                            hls=course.get("hls"),
                            language=course.get("language"),
                            desktop_available=course.get("desktopAvailable"),
                            created_by=str(course.get("createdBy")) if course.get("createdBy") else None,
                            creation_stage=course.get("creationStage"),
                            publish_status=course.get("publishStatus"),
                            is_deleted=course.get("isDeleted"),
                            deleted_by=course.get("deletedBy"),
                            deleted_at=course.get("deletedAt"),
                            created_at=course.get("createdAt"),
                        )
                        for course in found_courses_data
                    ]

                # --- Convert Banner to Base64 ---
                banner_base64_data = None
                if pkg.get("bannerUrl"):
                    file_path = os.path.normpath(os.path.join(pkg["bannerUrl"].lstrip('/')))
                    try:
                        with open(file_path, "rb") as image_file:
                            banner_base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                    except FileNotFoundError:
                        logger.warning(f"get_packages: Banner file not found at {file_path}")
                    except Exception as e:
                        logger.error(f"get_packages: Error reading banner file: {str(e)}")

                # --- Convert Theme to Base64 ---
                theme_base64_data = None
                if pkg.get("themeUrl"):
                    file_path = os.path.normpath(os.path.join(pkg["themeUrl"].lstrip('/')))
                    try:
                        with open(file_path, "rb") as image_file:
                            theme_base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                    except FileNotFoundError:
                        logger.warning(f"get_packages: Theme file not found at {file_path}")
                    except Exception as e:
                        logger.error(f"get_packages: Error reading theme file: {str(e)}")

                # --- Format FAQs ---
                response_faqs = []
                if pkg.get("faqs"):
                    response_faqs = [
                        FaqType(question=f.get('question'), answer=f.get('answer'))
                        for f in pkg.get("faqs", [])
                    ]

                # --- Format Price Details ---
                response_price_details = [
                    PriceType(
                        period=p.get("period"),
                        actual_price=p.get("actualPrice", p.get("actual_price")),
                        price=p.get("price"),
                        gst=p.get("gst"),
                        totalprice=p.get('totalprice')
                    ) for p in pkg.get("price_details", [])
                ] if pkg.get("price_details") else []

                # --- Prepare Final Response ---
                package_response = PackageDetailsType(
                    id=str(pkg["_id"]),
                    title=pkg.get("title", ""),
                    description=pkg.get("description"),
                    banner_url=pkg.get("bannerUrl"),
                    theme_url=pkg.get("themeUrl"),
                    banner_base64=banner_base64_data,
                    theme_base64=theme_base64_data,
                    is_active=pkg.get("isActive"),
                    is_deleted=pkg.get("isDeleted"),
                    is_draft=pkg.get("isDraft"),
                    status=pkg.get("status", "active"),  # <-- Added missing field
                    created_at=pkg.get("createdAt"),
                    updated_at=pkg.get("updatedAt"),
                    created_by=pkg.get("createdBy"),
                    updated_by=pkg.get("updatedBy"),
                    course_ids=pkg.get("course_ids", []),
                    course_details=course_details_list,
                    # price=pkg.get("price", 0.0),  # OLD field (keeping if needed)
                    price_details=response_price_details,  # <-- Added missing field
                    telegram_id=pkg.get("telegram_id", []),
                    faqs=response_faqs,
                    deleted_at=pkg.get("deletedAt"),
                    deleted_by=pkg.get("deletedBy"),
                )
                result_packages.append(package_response)

            logger.info(f"get_packages: Successfully fetched {len(result_packages)} packages")
            return result_packages

        except Exception as e:
            logger.error(f"get_packages: An unexpected error occurred: {str(e)}")
            print(f"An unexpected error occurred in get_packages: {e}")
            return []

# --- GraphQL Mutations ---
@strawberry.type
class Mutation:
    # FIXES: Converted to async function and added 'await' to all database calls.
    @strawberry.mutation
    async def signup(self, input: UserInput) -> UserResponse:
        logger.info(f"Entering signup with input: name={input.name}, email={input.email}, phone={input.phone}")
        try:
            # ----------------- VALIDATION CHECKS -----------------
            # Phone number validation (exactly 10 digits)
            if not input.phone.isdigit() or len(input.phone) != 10:
                result = UserResponse(status=400, message="Phone number must be exactly 10 digits.")
                logger.info(f"signup: Validation failed - {result.message}")
                return result

            # Email format validation
            if not re.match(r"[^@]+@[^@]+\.[^@]+", input.email):
                result = UserResponse(status=400, message="Invalid email format.")
                logger.info(f"signup: Validation failed - {result.message}")
                return result

            # Password complexity validation
            if len(input.password) < 8 or not any(c.isupper() for c in input.password) or not any(c.islower() for c in input.password) or not any(c.isdigit() for c in input.password):
                result = UserResponse(status=400, message="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one digit.")
                logger.info(f"signup: Validation failed - {result.message}")
                return result
            # -----------------------------------------------------

            # FIX: Added await
            if await users_collection.find_one({"email": input.email}):
                result = UserResponse(status=409, message=f"User with email '{input.email}' already exists.")
                logger.info(f"signup: {result.message}")
                return result
            
            # FIX: Added await
            if await users_collection.find_one({"phone": input.phone}):
                result = UserResponse(status=409, message=f"User with phone '{input.phone}' already exists.")
                logger.info(f"signup: {result.message}")
                return result
            
            # FIX: Added await
            default_usertype = await usertypes_collection.find_one({"usertype": "user"})
            
            if not default_usertype:
                result = UserResponse(status=404, message="Default 'user' usertype not found.")
                logger.info(f"signup: {result.message}")
                return result
            
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
            
            # FIX: Added await
            insert_result = await users_collection.insert_one(user_dict)
            
            new_user_id = insert_result.inserted_id
            
            payload = {
                "id": str(new_user_id),
                "name": new_user_data.name,
                "email": new_user_data.email,
                "phone": new_user_data.phone,
                "usertype": "user",
                "jti": str(uuid.uuid4())
            }

            token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
            
            login_entry_data = LoginModel(user_id=new_user_id, token=token)
            
            # FIX: Added await
            await logins_collection.insert_one(login_entry_data.model_dump(by_alias=True, exclude_none=True))
            
            result = UserResponse(
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
            logger.info(f"signup: Successfully signed up user with id {new_user_id}")
            return result
        except (PyMongoError, ValidationError) as e:
            logger.error(f"signup: Error occurred: {str(e)}")
            return UserResponse(status=500, message=f"An unexpected error occurred: {e}")
        
    @strawberry.mutation
    async def login(self, email: str, password: str) -> UserResponse:
        logger.info(f"Entering login with email: {email}")
        try:
            print(f"Attempting to log in with email: {email}")
            
            # CORRECTED: Added 'await' before find_one()
            user_doc = await users_collection.find_one({"email": email, "isDeleted": False})
            
            if not user_doc:
                result = UserResponse(status=404, message="User not found or is deleted.")
                logger.info(f"login: {result.message}")
                return result
            
            if not bcrypt.checkpw(password.encode('utf-8'), user_doc["password"].encode('utf-8')):
                result = UserResponse(status=401, message="Incorrect email or password.")
                logger.info(f"login: {result.message}")
                return result
            
            # CORRECTED: Added 'await' before find_one() for usertype_doc
            usertype_doc = await usertypes_collection.find_one({"_id": ObjectId(user_doc["usertype_id"])})
            
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
            
            # CORRECTED: Added 'await' before update_one()
            await logins_collection.update_one(
                {"user_id": user_doc["_id"]},
                {"$set": {"token": token, "created_at": datetime.utcnow()}},
                upsert=True
            )
            
            result = UserResponse(
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
            logger.info(f"login: Successfully logged in user with email {email}")
            return result
            
        except PyMongoError as e:
            logger.error(f"login: Database error: {str(e)}")
            return UserResponse(status=500, message=f"Database error: {e}")
        except Exception as e:
            logger.error(f"login: Unexpected error: {str(e)}")
            return UserResponse(status=500, message=f"Unexpected error: {e}")

    # @strawberry.type
    # class Mutation:
    # @strawberry.mutation
    # async def create_package(
    #     self,
    #     info: strawberry.Info,
    #     title: str,
    #     description: str,
    #     banner_file: Upload,
    #     theme_file: Upload,
    #     price: float,
    #     course_ids: Optional[List[str]] = None,
    #     telegram_id: Optional[List[str]] = None,
    #     faqs: Optional[List[FaqInput]] = None,
    #     is_draft: Optional[bool] = None
    # ) -> PackageResponse:
    #     logger.info(f"Entering create_package with title: {title}, description: {description}, price: {price}, course_ids: {course_ids}, telegram_id: {telegram_id}, is_draft: {is_draft}")
    #     banner_url = None
    #     theme_url = None
    #     banner_base64_data = None
    #     theme_base64_data = None
        
    #     try:
    #         current_user: Optional[AuthenticatedUser] = info.context.get("current_user")
    #         if not current_user:
    #             result = PackageResponse(status=401, message="Authentication required: You must be logged in.")
    #             logger.info(f"create_package: {result.message}")
    #             return result
    #         created_by_id = current_user.id
    #         print(created_by_id)
    #         print(title)
    #         # CORRECTED: Await the database call
    #         if await packages_collection.find_one({"title": title, "isDeleted": False}):
    #             result = PackageResponse(status=409, message=f"Package with title '{title}' already exists.")
    #             logger.info(f"create_package: {result.message}")
    #             return result
    #         print(banner_file)
    #         # CORRECTED: Await reading the file content
    #         banner_content = await banner_file.read()
    #         # print('banner_content:',banner_content)
    #         theme_content = await theme_file.read()
    #         banner_base64_data = base64.b64encode(banner_content).decode('utf-8')
    #         theme_base64_data = base64.b64encode(theme_content).decode('utf-8')

    #         # CORRECTED: Await resetting the file pointer
    #         await banner_file.seek(0)
    #         await theme_file.seek(0)

    #         banner_url = await save_and_compress_file(banner_file, "banners")
    #         print(banner_url)
    #         theme_url = await save_and_compress_file(theme_file, "themes")
    #         print(theme_url)

    #         if not course_ids and not telegram_id:
    #             result = PackageResponse(status=400, message="Either course_ids or telegram_id must be provided.")
    #             logger.info(f"create_package: {result.message}")
    #             return result

    #         if course_ids:
    #             course_object_ids = [ObjectId(cid) for cid in course_ids]
    #             # CORRECTED: Await the .to_list() method on the async cursor
    #             found_courses = await courses_collection.find({"_id": {"$in": course_object_ids}}).to_list(length=None)
    #             if len(found_courses) != len(course_ids):
    #                 result = PackageResponse(status=404, message="One or more course IDs not found.")
    #                 logger.info(f"create_package: {result.message}")
    #                 return result

    #         faqs_data = [FaqModel(question=faq.question, answer=faq.answer) for faq in faqs] if faqs else []
    #         print(faqs_data)
    #         is_draft_value = is_draft if is_draft is not None else False
    #         print(is_draft_value)

    #         new_package_data = PackageModel(
    #             title=title,
    #             description=description,
    #             banner_url=banner_url,
    #             theme_url=theme_url,
    #             created_by=created_by_id,
    #             course_ids=course_ids if course_ids else [],
    #             price=price,
    #             telegram_id=telegram_id if telegram_id else [],
    #             faqs=faqs_data,
    #             is_draft=is_draft_value
    #         )

    #         package_dict = new_package_data.model_dump(by_alias=True, exclude_none=True)
            
    #         # CORRECTED: Await inserting the new document
    #         insert_result = await packages_collection.insert_one(package_dict)

    #         # CORRECTED: Await finding the new document
    #         new_package_doc = await packages_collection.find_one({"_id": insert_result.inserted_id})

    #         if not new_package_doc:
    #             logger.error("create_package: Failed to retrieve the newly created package.")
    #             raise Exception("Failed to retrieve the newly created package.")

    #         response_faqs = [FaqType(question=f.get('question'), answer=f.get('answer')) for f in new_package_doc.get("faqs", [])]

    #         result = PackageResponse(
    #             status=201,
    #             message="Package created successfully.",
    #             data=PackageDetailsType(
    #                 id=str(new_package_doc["_id"]),
    #                 title=new_package_doc.get("title"),
    #                 description=new_package_doc.get("description"),
    #                 banner_url=new_package_doc.get("bannerUrl"),
    #                 theme_url=new_package_doc.get("themeUrl"),
    #                 banner_base64=banner_base64_data,
    #                 theme_base64=theme_base64_data,
    #                 is_active=new_package_doc.get("isActive"),
    #                 is_deleted=new_package_doc.get("isDeleted"),
    #                 created_at=new_package_doc.get("createdAt"),
    #                 updated_at=new_package_doc.get("updatedAt"),
    #                 created_by=new_package_doc.get("createdBy"),
    #                 updated_by=new_package_doc.get("updatedBy"),
    #                 course_ids=new_package_doc.get("course_ids", []),
    #                 price=new_package_doc.get("price", 0.0),
    #                 telegram_id=new_package_doc.get("telegram_id", []),
    #                 faqs=response_faqs,
    #                 deleted_at=None,
    #                 deleted_by=None,
    #                 # isDraft=new_package_doc.get("isDraft", False)
    #                 is_draft=new_package_doc.get("isDraft", False)
    #             )
    #         )
    #         logger.info(f"create_package: Successfully created package with id {new_package_doc['_id']}")
    #         return result

    #     except (PyMongoError, ValidationError) as e:
    #         if banner_url:
    #             delete_previous_file(banner_url.lstrip('/'))
    #         if theme_url:
    #             delete_previous_file(theme_url.lstrip('/'))
    #         logger.error(f"create_package: Database or validation error: {str(e)}")
    #         return PackageResponse(status=500, message=f"A database or validation error occurred: {e}")
    #     except Exception as e:
    #         if banner_url:
    #             delete_previous_file(banner_url.lstrip('/'))
    #         if theme_url:
    #             delete_previous_file(theme_url.lstrip('/'))
    #         logger.error(f"create_package: Unexpected error: {str(e)}")
    #         return PackageResponse(status=500, message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    async def create_package(
        self,
        info: strawberry.Info,
        title: Optional[str] = None,  # Made optional for is_draft=True
        description: Optional[str] = None, # Made optional for is_draft=True
        banner_file: Optional[Upload] = None, # Made optional for is_draft=True
        theme_file: Optional[Upload] = None, # Made optional for is_draft=True
        price_details: Optional[List[PriceInput]] = None, # New optional parameter for price details
        course_ids: Optional[List[str]] = None,
        telegram_id: Optional[List[str]] = None,
        faqs: Optional[List[FaqInput]] = None,
        is_draft: Optional[bool] = None,
        status: Optional[str] = None # New optional parameter for package status
    ) -> PackageResponse:
        logger.info(f"Entering create_package with title: {title}, description: {description}, price_details: {price_details}, course_ids: {course_ids}, telegram_id: {telegram_id}, is_draft: {is_draft}, status: {status}")
        banner_url = None
        theme_url = None
        banner_base64_data = None
        theme_base64_data = None
        
        try:
            current_user: Optional[AuthenticatedUser] = info.context.get("current_user")
            if not current_user:
                result = PackageResponse(status=401, message="Authentication required: You must be logged in.")
                logger.info(f"create_package: {result.message}")
                return result
            created_by_id = current_user.id

            # Enhanced: Handle mandatory fields only if not a draft
            is_draft_value = is_draft if is_draft is not None else False
            if not is_draft_value:
                # Ensure all mandatory fields are present for a non-draft package
                if not title:
                    return PackageResponse(status=400, message="Title is required for a non-draft package.")
                if not description:
                    return PackageResponse(status=400, message="Description is required for a non-draft package.")
                if not banner_file or not theme_file:
                    return PackageResponse(status=400, message="Both banner and theme files are required for a non-draft package.")
                if not price_details:
                    return PackageResponse(status=400, message="Price details are required for a non-draft package.")
                if not course_ids and not telegram_id:
                    return PackageResponse(status=400, message="Either course_ids or telegram_id must be provided for a non-draft package.")

                # Enhanced: Await the database call only if title is provided
                if await packages_collection.find_one({"title": title, "isDeleted": False}):
                    result = PackageResponse(status=409, message=f"Package with title '{title}' already exists.")
                    logger.info(f"create_package: {result.message}")
                    return result
            
            # Enhanced: Conditional file processing
            if banner_file:
                banner_content = await banner_file.read()
                theme_content = await theme_file.read()
                banner_base64_data = base64.b64encode(banner_content).decode('utf-8')
                theme_base64_data = base64.b64encode(theme_content).decode('utf-8')

                # Await resetting the file pointer
                await banner_file.seek(0)
                await theme_file.seek(0)

                banner_url = await save_and_compress_file(banner_file, "banners")
                theme_url = await save_and_compress_file(theme_file, "themes")

            # Original logic for course_ids and telegram_id
            # if course_ids:
            if not is_draft_value and course_ids:
                course_object_ids = [ObjectId(cid) for cid in course_ids]
                found_courses = await courses_collection.find({"_id": {"$in": course_object_ids}}).to_list(length=None)
                if len(found_courses) != len(course_ids):
                    result = PackageResponse(status=404, message="One or more course IDs not found.")
                    logger.info(f"create_package: {result.message}")
                    return result

            faqs_data = [FaqModel(question=faq.question, answer=faq.answer) for faq in faqs] if faqs else []

            # Enhanced: Prepare price data
            price_data = [PriceModel(
                period=p.period,
                actual_price=p.actual_price,
                price=p.price,
                gst=p.gst,
                totalprice=p.totalprice
            ) for p in price_details] if price_details else []

            # Enhanced: Determine status
            status_value = status if status else "active" # Default status to 'active' if not provided

            new_package_data = PackageModel(
                title=title,
                description=description,
                banner_url=banner_url,
                theme_url=theme_url,
                created_by=created_by_id,
                course_ids=course_ids if course_ids else [],
                # Enhanced: Save the list of price details
                price_details=price_data,
                telegram_id=telegram_id if telegram_id else [],
                faqs=faqs_data,
                is_draft=is_draft_value,
                status=status_value # Save the new status field
            )

            package_dict = new_package_data.model_dump(by_alias=True, exclude_none=True)
            
            insert_result = await packages_collection.insert_one(package_dict)
            new_package_doc = await packages_collection.find_one({"_id": insert_result.inserted_id})

            if not new_package_doc:
                logger.error("create_package: Failed to retrieve the newly created package.")
                raise Exception("Failed to retrieve the newly created package.")

            response_faqs = [FaqType(question=f.get('question'), answer=f.get('answer')) for f in new_package_doc.get("faqs", [])]
            
            # Enhanced: Prepare response price details
            response_price_details = [PriceType(
                period=p.get('period'),
                actual_price=p.get("actualPrice", p.get("actual_price")),
                price=p.get('price'),
                gst=p.get('gst'),
                totalprice=p.get('totalprice')
            ) for p in new_package_doc.get("price_details", [])]

            result = PackageResponse(
                status=201,
                message="Package created successfully.",
                data=PackageDetailsType(
                    id=str(new_package_doc["_id"]),
                    title=new_package_doc.get("title"),
                    description=new_package_doc.get("description"),
                    banner_url=new_package_doc.get("bannerUrl"),
                    theme_url=new_package_doc.get("themeUrl"),
                    banner_base64=banner_base64_data,
                    theme_base64=theme_base64_data,
                    is_active=new_package_doc.get("isActive"),
                    is_deleted=new_package_doc.get("isDeleted"),
                    created_at=new_package_doc.get("createdAt"),
                    updated_at=new_package_doc.get("updatedAt"),
                    created_by=new_package_doc.get("createdBy"),
                    updated_by=new_package_doc.get("updatedBy"),
                    course_ids=new_package_doc.get("course_ids", []),
                    # price=new_package_doc.get("price", 0.0), # Removed old price field
                    price_details=response_price_details, # New price details field
                    telegram_id=new_package_doc.get("telegram_id", []),
                    faqs=response_faqs,
                    deleted_at=None,
                    deleted_by=None,
                    is_draft=new_package_doc.get("isDraft", False),
                    status=new_package_doc.get("status", "active") # New status field
                )
            )
            logger.info(f"create_package: Successfully created package with id {new_package_doc['_id']}")
            return result

        except (PyMongoError, ValidationError) as e:
            if banner_url:
                delete_previous_file(banner_url.lstrip('/'))
            if theme_url:
                delete_previous_file(theme_url.lstrip('/'))
            logger.error(f"create_package: Database or validation error: {str(e)}")
            return PackageResponse(status=500, message=f"A database or validation error occurred: {e}")
        except Exception as e:
            if banner_url:
                delete_previous_file(banner_url.lstrip('/'))
            if theme_url:
                delete_previous_file(theme_url.lstrip('/'))
            logger.error(f"create_package: Unexpected error: {str(e)}")
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
        price_details: Optional[List[PriceInput]] = None,
        telegram_id: Optional[List[str]] = None,
        faqs: Optional[List[FaqInput]] = None,
        is_draft: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> PackageResponse:
        logger.info(f"Entering update_package with package_id: {package_id}, title: {title}, description: {description}, course_ids: {course_ids}, price_details: {price_details}, telegram_id: {telegram_id}, is_draft: {is_draft}, status: {status}")

        try:
            # ----------------- AUTHENTICATION CHECK (COMMENTED FOR DEVELOPMENT) -----------------
            current_user: Optional[AuthenticatedUser] = info.context.get("current_user")
            if not current_user:
                result = PackageResponse(status=401, message="Authentication required: You must be logged in.")
                logger.info(f"update_package: {result.message}")
                return result
            # ------------------------------------------------------------------------------------

            existing_package_doc = await packages_collection.find_one({"_id": ObjectId(package_id)})
            if not existing_package_doc:
                result = PackageResponse(status=404, message="Package not found.")
                logger.info(f"update_package: {result.message}")
                return result
            
            # ----------------- OWNERSHIP CHECK (COMMENTED FOR DEVELOPMENT) -----------------
            # if str(existing_package_doc.get("createdBy")) != current_user.id:
            #    raise Exception("Unauthorized: You do not have permission to update this package.")
            updated_by_id = current_user.id
            # -------------------------------------------------------------------------------

            # ----------------- DEVELOPMENT PLACEHOLDER (UNCOMMENTED) -----------------
            # updated_by_id = "development_user"
            # -----------------------------------------------------------------------------

            update_data = {}

            # Handle banner file update
            if banner_file:
                if existing_package_doc.get("bannerUrl"):
                    await delete_previous_file(existing_package_doc["bannerUrl"].lstrip('/'))
                
                update_data["bannerUrl"] = await save_and_compress_file(banner_file, "banners")
            else:
                update_data["bannerUrl"] = existing_package_doc.get("bannerUrl")
            
            # Handle theme file update
            if theme_file:
                if existing_package_doc.get("themeUrl"):
                    await delete_previous_file(existing_package_doc["themeUrl"].lstrip('/'))

                update_data["themeUrl"] = await save_and_compress_file(theme_file, "themes")
            else:
                update_data["themeUrl"] = existing_package_doc.get("themeUrl")


            # Update scalar fields if provided
            if title is not None:
                update_data["title"] = title
            if description is not None:
                update_data["description"] = description
            if telegram_id is not None:
                update_data["telegram_id"] = telegram_id
            
            # Handle price_details
            if price_details is not None:
                # update_data["priceDetails"] = [
                update_data["price_details"] = [
                    PriceModel(
                        period=p.period, 
                        actual_price=p.actual_price, 
                        price=p.price, 
                        gst=p.gst,
                        totalprice=p.totalprice
                    ).model_dump(by_alias=True) for p in price_details
                ]
                
            # Handle is_draft and status
            if is_draft is not None:
                update_data["isDraft"] = is_draft
            if status is not None:
                update_data["status"] = status
            
            # Handle faqs
            if faqs is not None:
                faq_docs = [{"question": faq.question, "answer": faq.answer} for faq in faqs]
                update_data["faqs"] = faq_docs

            # Handle course_ids and add draft-specific validation logic
            if course_ids is not None:
                is_now_draft = update_data.get("isDraft", existing_package_doc.get("isDraft"))
                if not is_now_draft:
                    course_object_ids = [ObjectId(cid) for cid in course_ids]
                    found_courses = await courses_collection.find({"_id": {"$in": course_object_ids}}).to_list(length=None)
                    if len(found_courses) != len(course_ids):
                        result = PackageResponse(status=404, message="One or more course IDs not found.")
                        logger.info(f"update_package: {result.message}")
                        return result
                update_data["course_ids"] = course_ids
                
            # Set common update fields
            update_data["updatedBy"] = updated_by_id
            update_data["updatedAt"] = datetime.utcnow()

            # Perform the update operation
            update_result = await packages_collection.update_one(
                {"_id": ObjectId(package_id)},
                {"$set": update_data}
            )

            if update_result.modified_count == 1:
                updated_package_doc = await packages_collection.find_one({"_id": ObjectId(package_id)})
                
                # Prepare the response data, handling the new fields
                response_faqs = [FaqType(**doc) for doc in updated_package_doc.get("faqs", [])]
                response_price_details = [
                    PriceType(
                        period=p.get('period'),
                        actual_price=p.get('actualPrice'),
                        price=p.get('price'),
                        gst=p.get('gst'),
                        totalprice=p.get('totalprice')
                    ) for p in updated_package_doc.get("price_details", [])
                ]

                result = PackageResponse(
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
                        is_draft=updated_package_doc.get("isDraft"),
                        status=updated_package_doc.get("status"),
                        created_at=updated_package_doc.get("createdAt"),
                        updated_at=updated_package_doc.get("updatedAt"),
                        created_by=updated_package_doc.get("createdBy"),
                        updated_by=updated_package_doc.get("updatedBy"),
                        course_ids=updated_package_doc.get("course_ids"),
                        price_details=response_price_details,
                        telegram_id=updated_package_doc.get("telegram_id"),
                        deleted_at=updated_package_doc.get("deletedAt"),
                        deleted_by=updated_package_doc.get("deletedBy"),
                        faqs=response_faqs
                    )
                )
                logger.info(f"update_package: Successfully updated package with id {package_id}")
                return result
            else:
                result = PackageResponse(status=500, message="Failed to update package.")
                logger.info(f"update_package: {result.message}")
                return result
                
        except (PyMongoError, ValueError, ValidationError) as e:
            logger.error(f"update_package: A database or validation error occurred: {str(e)}")
            return PackageResponse(status=500, message=f"A database or validation error occurred: {e}")
        except Exception as e:
            logger.error(f"update_package: Unexpected error: {str(e)}")
            return PackageResponse(status=500, message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    async def delete_package(
        self,
        info: strawberry.Info,
        package_id: str
    ) -> PackageResponse:
        logger.info(f"Entering delete_package with package_id: {package_id}")
        try:
            # ----------------- AUTHENTICATION CHECK -----------------
            # For development, you can use the commented out code
            # deleted_by_id = "development_user"
            current_user: Optional[AuthenticatedUser] = info.context.get("current_user")
            if not current_user:
                result = PackageResponse(status=401, message="Authentication required: You must be logged in.")
                logger.info(f"delete_package: {result.message}")
                return result
            deleted_by_id = current_user.id
            # --------------------------------------------------------

            existing_package_doc = await packages_collection.find_one({"_id": ObjectId(package_id)})
            if not existing_package_doc:
                result = PackageResponse(status=404, message="Package not found.")
                logger.info(f"delete_package: {result.message}")
                return result
            
            # ----------------- OWNERSHIP CHECK -----------------
            # if str(existing_package_doc.get("createdBy")) != current_user.id:
            #     raise Exception("Unauthorized: You do not have permission to delete this package.")
            # ---------------------------------------------------

            update_result = await packages_collection.update_one(
                {"_id": ObjectId(package_id)},
                {"$set": {
                    "isDeleted": True,
                    # "updatedAt": datetime.utcnow(),
                    # "updatedBy": deleted_by_id,
                    "deletedAt": datetime.utcnow(),
                    "deletedBy": deleted_by_id
                }}
            )

            if update_result.modified_count == 1:
                updated_package_doc = await packages_collection.find_one({"_id": ObjectId(package_id)})
                result = PackageResponse(
                    status=200,
                    message="Package deleted successfully.",
                    data=PackageDetailsType(
                        id=str(updated_package_doc["_id"]),
                        title=updated_package_doc.get("title"),
                        description=updated_package_doc.get("description"),
                        banner_url=updated_package_doc.get("bannerUrl"),
                        theme_url=updated_package_doc.get("themeUrl"),
                        banner_base64=None,  # Not stored in DB, only used for upload
                        theme_base64=None,   # Not stored in DB, only used for upload
                        is_active=updated_package_doc.get("isActive", False),
                        is_deleted=updated_package_doc.get("isDeleted", True),
                        is_draft=updated_package_doc.get("isDraft", False),
                        status=None,  # Can be computed later if needed
                        created_at=updated_package_doc.get("createdAt"),
                        updated_at=updated_package_doc.get("updatedAt"),
                        created_by=updated_package_doc.get("createdBy"),
                        updated_by=updated_package_doc.get("updatedBy"),
                        deleted_at=updated_package_doc.get("deletedAt"),
                        deleted_by=updated_package_doc.get("deletedBy"),
                        price_details=[
                            PriceType(
                                period=price.get("period"),
                                actual_price=price.get("actualPrice", 0.0),
                                price=price.get("price", 0.0),
                                gst=price.get("gst", 0.0),
                                totalprice=price.get("totalprice",0.0)
                            ) for price in updated_package_doc.get("price_details", [])
                        ],
                        course_ids=updated_package_doc.get("course_ids", []),
                        course_details=None,  # Needs population separately
                        telegram_id=updated_package_doc.get("telegram_id", []),
                        faqs=[
                            FaqType(
                                question=faq.get("question"),
                                answer=faq.get("answer")
                            ) for faq in updated_package_doc.get("faqs", [])
                        ]
                    )
                )
                logger.info(f"delete_package: Successfully deleted package with id {package_id}")
                return result
            else:
                result = PackageResponse(status=500, message="Failed to delete package.")
                logger.info(f"delete_package: {result.message}")
                return result
        except (PyMongoError, ValueError) as e:
            logger.error(f"delete_package: Error occurred: {str(e)}")
            return PackageResponse(status=500, message=f"An error occurred: {e}")
        except Exception as e:
            logger.error(f"delete_package: Unexpected error: {str(e)}")
            return PackageResponse(status=500, message=f"An unexpected error occurred: {e}")

    @strawberry.mutation
    async def create_purchase(
        self,
        user_id: str,
        name: str,
        email: str,
        phone: str,
        courses: List[CourseProgressInput],
        package_id: Optional[str] = None
    ) -> str:

        # Convert courses to dicts with certificate_sent default
        courses_data = [
            {**course.__dict__, "certificate_sent": False} for course in courses
        ]

        logger.info(f"Creating purchase for user_id={user_id}, package_id={package_id}")

        # Package purchase
        if package_id:
            existing = await purchased_collection.find_one({
                "user_id": user_id,
                "package_id": package_id
            })
            if existing:
                logger.info(f"Existing package found for user {user_id}, updating courses")
                existing_courses = {c["course_id"]: c for c in existing["courses"]}
                for course in courses_data:
                    existing_courses[course["course_id"]] = course
                await purchased_collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "courses": list(existing_courses.values()),
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "updated_at": datetime.utcnow()
                    }}
                )
                return str(existing["_id"])

            new_purchase = {
                "user_id": user_id,
                "name": name,
                "email": email,
                "phone": phone,
                "package_id": package_id,
                "courses": courses_data,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await purchased_collection.insert_one(new_purchase)
            logger.info(f"New package purchase created with id={result.inserted_id}")
            return str(result.inserted_id)

        # Single course purchase
        inserted_ids = []
        for course in courses_data:
            existing = await purchased_collection.find_one({
                "user_id": user_id,
                "package_id": None,
                "courses": {"$elemMatch": {"course_id": course["course_id"]}}
            })
            if existing:
                logger.info(f"Updating existing course {course['course_id']} for user {user_id}")
                await purchased_collection.update_one(
                    {"_id": existing["_id"], "courses.course_id": course["course_id"]},
                    {"$set": {
                        "courses.$.course_view_percent": course["course_view_percent"],
                        "courses.$.certificate_sent": course["certificate_sent"],
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "updated_at": datetime.utcnow()
                    }}
                )
                inserted_ids.append(str(existing["_id"]))
            else:
                new_purchase = {
                    "user_id": user_id,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "package_id": None,
                    "courses": [course],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                result = await purchased_collection.insert_one(new_purchase)
                logger.info(f"New single course purchase created with id={result.inserted_id}")
                inserted_ids.append(str(result.inserted_id))

        return ", ".join(inserted_ids)


    @strawberry.mutation
    async def update_course_progress(
        self,
        purchase_id: str,
        course_id: str,
        view_percent: float,
        certificate_sent: Optional[bool] = None
    ) -> str:
        """
        Updates course progress (view_percent) and optionally certificate_sent
        for a specific course in a user's purchase.
        """

        logger.info(f"Updating course progress: purchase_id={purchase_id}, course_id={course_id}")

        # Check if purchase exists
        purchase = await purchased_collection.find_one({"_id": ObjectId(purchase_id)})
        if not purchase:
            logger.warning(f"Purchase with id={purchase_id} not found")
            return f"Purchase with id={purchase_id} does not exist."

        # Prepare update data
        update_data = {
            "courses.$[elem].course_view_percent": view_percent,
            "updated_at": datetime.utcnow()
        }
        if certificate_sent is not None:
            update_data["courses.$[elem].certificate_sent"] = certificate_sent

        # Perform the update with array_filters
        result = await purchased_collection.update_one(
            {"_id": ObjectId(purchase_id)},
            {"$set": update_data},
            array_filters=[{"elem.course_id": course_id}]
        )

        if result.modified_count == 0:
            logger.info(f"No changes made for course {course_id} in purchase {purchase_id}")
            return "No course found or no changes made."
        
        logger.info(f"Course progress updated successfully for course {course_id} in purchase {purchase_id}")
        return "Course progress updated successfully."

# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)