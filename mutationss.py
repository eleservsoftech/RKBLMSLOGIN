import bcrypt
import strawberry
import base64
import uuid
import os
from PIL import Image
from typing import List, Optional, Union,Dict,Any,Set,Tuple
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
from collections import Counter
from datetime import datetime, timezone, MINYEAR
from dateutil.relativedelta import relativedelta
import math

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
    courseprice_collection,
    courselession_table,
    progress_collection
   
)
# ... (existing imports)
from models import (
    UserModel,
    LoginModel,
    UserTypeModel,
    PackageModel,
    PriceModel,
    FaqModel, # NEW: Import FaqModel from your models file
    CourseProgressModel,
    CourseWatchModel
)

# ----------------- AUTHENTICATION CODE (COMMENTED FOR DEVELOPMENT) -----------------
from authenticate import AuthenticatedUser
# -----------------------------------------------------------------------------------

# --- GraphQL Types ---

@strawberry.type
class LessonPercentageType:
    """
    Holds the calculated progress for a single lesson.
    """
    lesson_id: str
    progress_percent: float

@strawberry.type
class CourseProgressPercentages:
    """
    The new, simple response object containing just the percentages.
    """
    total_progress_percent: float
    lesson_progress: List[LessonPercentageType]

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

    purchase_count: Optional[int] = 0   # ✅ NEW FIELD

@strawberry.input
class FaqInput:
    question: str
    answer: str

@strawberry.input
class PurchaseFilterInput:
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    admin_analysis: Optional[bool] = False

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

    purchase_count: Optional[int] = 0   # ✅ NEW FIELD
    

    
   

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

@strawberry.type
class CourseOutput:
    course_id: str
    course_view_percent: float
    certificate_sent: bool


@strawberry.type
class PurchaseOutput:
    purchase_id: Optional[str]          # ✅ New field added
    package_id: Optional[str]
    courses: List[CourseOutput]
    created_at: datetime

@strawberry.type
class UserPurchaseOutput:
    user_id: str
    purchases: List[PurchaseOutput]


@strawberry.type
class AdminAnalysisOutput:
    total_users: int
    total_purchases: int
    total_courses: int
    completed_courses: int
    certificate_sent_true: int
    certificate_sent_false: int
    certificate_sent_true_users: List[UserType]
    certificate_sent_false_users: List[UserType]
    most_purchased_course: Optional[str]
    most_purchased_package: Optional[str]
    most_purchased_course_details: Optional[CourseDetailsType]
    most_purchased_package_details: Optional[PackageDetailsType]
    all_purchased_courses: Optional[List[CourseDetailsType]] = None
    all_purchased_packages: Optional[List[PackageDetailsType]] = None

@strawberry.type
class AllPurchaseOutput:
    all_purchases: List[PurchaseOutput]

@strawberry.type
class UserListResponse:
    total_count: int
    active_count: int
    users: List[UserType]
    ## new added
    deleted_count: int
    deleted_users: List[UserType]

@strawberry.type
class StatusCountType:
    status: str
    count: int
@strawberry.type
class CourseListResponse:
    total_count: int
    status_counts: List[StatusCountType]
    courses: List[CourseDetailsType]

@strawberry.type
class PackageStatusCountType:
    status: str
    count: int

@strawberry.type
class UpdateWatchTimeResponse:
    """
    The response from an updateLessonWatchTime mutation,
    containing success status and an optional message.
    """
    success: bool
    message: Optional[str] = None

# @strawberry.experimental.pydantic.type(model=CourseWatchModel, all_fields=True)
# class CourseWatchType:
#     pass
# # Use Strawberry's pydantic support to convert your Pydantic model
# @strawberry.experimental.pydantic.type(model=CourseProgressModel)
# class CourseProgressType:
#     id: strawberry.auto
#     user_id: strawberry.auto
#     course_id: strawberry.auto
#     lesson_ids: strawberry.auto
#     lesson_duration: strawberry.auto
#     course_duration: strawberry.auto
#     # NOTE: You might need a corresponding Strawberry type for CourseWatchModel 
#     # if you want to include watch_times in the final Type.
#     # For this simple init, we'll keep it basic.
#     total_watch_time: strawberry.auto
#     created_at: strawberry.auto
#     updated_at: strawberry.auto

@strawberry.type
class LessonProgressType:
    lesson_id: str
    progress_percent: float
    watch_time: float  # <--- The error means this line exists
# This type for your nested object looks perfect as-is
@strawberry.experimental.pydantic.type(model=CourseWatchModel, all_fields=True)
class CourseWatchType:
    pass


# --- ⭐️ THIS IS THE UPDATED TYPE ⭐️ ---
@strawberry.experimental.pydantic.type(model=CourseProgressModel)
class CourseProgressType:
    # --- Fields from your Pydantic model ---
    id: strawberry.auto
    user_id: strawberry.auto
    course_id: strawberry.auto
    
    # --- Add the new fields ---
    package_id: strawberry.auto
    expiry: strawberry.auto
    
    # --- Map the nested list ---
    watch_times: List[CourseWatchType]

    # --- Existing fields ---
    lesson_ids: strawberry.auto
    lesson_duration: strawberry.auto
    course_duration: strawberry.auto
    total_watch_time: strawberry.auto
    created_at: strawberry.auto
    updated_at: strawberry.auto


    # --- ⭐️ NEW COMPUTED FIELD ⭐️ ---
    
    @strawberry.field
    def days_left(self) -> Optional[int]:
        """
        Calculates the number of days remaining until the course expires.
        'self' here is the Pydantic CourseProgressModel instance.
        """
        if not self.expiry:
            return None # No expiry date is set

        # This is offset-aware
        now_utc = datetime.now(timezone.utc)
        
        # --- ⭐️ FIX IS HERE ⭐️ ---
        # Assume the naive 'self.expiry' from DB is UTC and make it aware
        if not self.expiry.tzinfo:
            expiry_aware = self.expiry.replace(tzinfo=timezone.utc)
        else:
            expiry_aware = self.expiry # It's already aware, just use it
        # --- END FIX ---
        
        # Check if expiry is in the past (now compares two aware datetimes)
        if expiry_aware < now_utc:
            return 0
        
        # Calculate time remaining
        time_remaining = expiry_aware - now_utc
        
        # Use math.ceil to round up to the nearest full day
        days_remaining = math.ceil(time_remaining.total_seconds() / (24 * 60 * 60))
        
        return int(days_remaining)
    
    # --- ⭐️ ADD THIS FIELD ⭐️ ---
    @strawberry.field
    def total_progress_percent(self) -> float:
        """Calculates the total course progress percentage."""
        return calculate_progress_percentage(
            self.total_watch_time, 
            self.course_duration
        )

    # --- ⭐️ ADD THIS FIELD ⭐️ ---
    @strawberry.field
    def lesson_progress(self) -> List[LessonProgressType]:
        """Returns a list of lessons with their progress percentage."""
        duration_map = {lid: dur for lid, dur in zip(self.lesson_ids, self.lesson_duration)}
        progress_list = []
        
        for lesson in self.watch_times:
            duration = duration_map.get(lesson.lesson_id, 0.0)
            percent = calculate_progress_percentage(lesson.watch_time, duration)
            
            progress_list.append(
                LessonProgressType(
                    lesson_id=lesson.lesson_id,
                    progress_percent=percent,
                    # --- ⭐️ ADD THIS LINE ⭐️ ---
                    watch_time=lesson.watch_time 
                )
            )
        return progress_list

# --- GraphQL Input Type (No Change) ---
@strawberry.input
class LessonWatchTimeInput:
    user_id: str  # ⬅️ CORRECTED: Use User ID to identify the user's document
    course_id: str
    lesson_id: str
    new_watch_time_seconds: int # The new, absolute watch time for the lesson

@strawberry.type
class PackageCountResponse:
    total_count: int = strawberry.field(name="totalCount")
    status_counts: List[PackageStatusCountType] = strawberry.field(name="statusCounts")
    packages: List[PackageDetailsType] = strawberry.field(name="packages")

def _to_maybe_object_id(s: str):
    """Try coercing a string id to ObjectId; fall back to the original string."""
    try:
        return ObjectId(s)
    except Exception:
        return s

def _map_user_doc_to_type(doc: Dict[str, Any]) -> UserType:
    return UserType(
        id=str(doc.get("_id")),
        name=doc.get("name") or "",
        email=doc.get("email") or "",
        phone=doc.get("phone") or "",
        usertype_id=str(doc.get("usertype_id") or ""),
        usertype=doc.get("usertype") or "",
        is_active=bool(doc.get("isActive", True)),
        is_deleted=bool(doc.get("isDeleted", False)),
        created_at=doc.get("createdAt") or doc.get("created_at") or datetime.utcnow(),
    )

def _map_course_doc_to_type(doc: Dict[str, Any]) -> CourseDetailsType:
    return CourseDetailsType(
        id=str(doc.get("_id")),
        title=doc.get("title") or "",
        description=doc.get("description"),
        thumbnail=doc.get("thumbnail"),
        hls=doc.get("hls"),
        language=doc.get("language"),
        desktop_available=bool(doc.get("desktopAvailable", True)),
        created_by=doc.get("createdBy"),
        creation_stage=doc.get("creationStage"),
        publish_status=doc.get("publishStatus"),
        is_deleted=bool(doc.get("isDeleted", False)),
        deleted_by=doc.get("deletedBy"),
        deleted_at=doc.get("deletedAt"),
        created_at=doc.get("createdAt") or doc.get("created_at") or datetime.utcnow(),
    )

def _map_package_doc_to_type(doc: Dict[str, Any]) -> PackageDetailsType:
    # NOTE: nested types like PriceType/FaqType/course_details can be filled later if needed.
    return PackageDetailsType(
        id=str(doc.get("_id")),
        title=doc.get("title") or "",
        description=doc.get("description"),
        banner_url=doc.get("bannerUrl"),
        theme_url=doc.get("themeUrl"),
        banner_base64=doc.get("banner_base64"),
        theme_base64=doc.get("theme_base64"),
        is_active=bool(doc.get("isActive", True)),
        is_deleted=bool(doc.get("isDeleted", False)),
        is_draft=bool(doc.get("isDraft", False)),
        status=doc.get("status"),
        created_at=doc.get("createdAt") or doc.get("created_at") or datetime.utcnow(),
        updated_at=doc.get("updatedAt") or doc.get("updated_at") or datetime.utcnow(),
        created_by=doc.get("createdBy"),
        updated_by=doc.get("updatedBy"),
        deleted_at=doc.get("deletedAt"),
        deleted_by=doc.get("deletedBy"),
        price_details=doc.get("price_details"),
        course_ids=[str(x) for x in (doc.get("course_ids") or [])],
        course_details=None,   # hydrate if you want (out of scope here)
        telegram_id=doc.get("telegram_id"),
        faqs=doc.get("faqs"),
    )


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


async def fetch_video_lessons_data(course_id: str) -> Tuple[List[str], List[float], float]:
    """
    Fetches lesson IDs and durations for all 'video' lessons in a course.
    """
    try:
        # We need to convert the string ID back to an ObjectId for the query
        course_oid = ObjectId(course_id) 
    except:
        # Handle case where course_id is not a valid ObjectId format
        print(f"Invalid course_id format: {course_id}")
        return [], [], 0.0

    try:
        pipeline = [
            {"$match": {
                "courseId": course_oid, 
                "lessonType": "video"
            }},
            {"$project": {
                "_id": 1, 
                "duration": 1  # Ensure this field exists and is numeric
            }}
        ]
        
        lesson_ids = []
        lesson_durations = []
        total_duration = 0.0

        async for doc in courselession_table.aggregate(pipeline):
            lesson_id = str(doc['_id']) 
            # Safely convert duration to float, default to 0 if missing/invalid
            duration = float(doc.get('duration', 0) or 0) 
            
            lesson_ids.append(lesson_id)
            lesson_durations.append(duration)
            total_duration += duration
            
        return lesson_ids, lesson_durations, total_duration

    except Exception as e:
        # Better to use a proper logger here!
        print(f"Error fetching lessons for course {course_id}: {e}")
        return [], [], 0.0
    
def parse_period_to_expiry_date(period_str: Optional[str]) -> Optional[datetime]:
    """
    Parses a string like "3months" or "1year" into a future datetime.
    """
    if not period_str:
        return None
    
    now = datetime.utcnow()
    
    # Regex to find the number (e.g., "3") and unit (e.g., "month")
    match = re.match(r"(\d+)\s*(month|year|day|week)s?", period_str, re.IGNORECASE)
    
    if not match:
        print(f"❌ Could not parse period string: {period_str}")
        return None
        
    value = int(match.group(1))
    unit = match.group(2).lower()
    
    try:
        if unit == "month":
            return now + relativedelta(months=value)
        elif unit == "year":
            return now + relativedelta(years=value)
        elif unit == "week":
            return now + relativedelta(weeks=value)
        elif unit == "day":
            return now + relativedelta(days=value)
    except Exception as e:
        print(f"❌ Error calculating expiry: {e}")
        return None
    
    print(f"❌ Unknown unit in period string: {period_str}")
    return None

def calculate_progress_percentage(watch_time: float, duration: float) -> float:
    """
    A reusable helper function to calculate progress.
    """
    if not duration or duration <= 0:
        return 0.0
    
    progress = (watch_time / duration) * 100
    
    # Cap at 100% and round to 2 decimal places
    return round(min(progress, 100.0), 2)

# --- GraphQL Queries ---
@strawberry.type
class Query:
    @strawberry.field(name="allUsers")
    async def all_users(
        self,
        active: Optional[bool] = None,          # None -> all; True -> only active; False -> only inactive (explicit)
        is_deleted: Optional[bool] = None       # None -> both; True -> only deleted; False -> only non-deleted (for users list only)
    ) -> UserListResponse:
        """
        - Counts are computed over non-deleted users (total_count, active_count), plus:
          deleted_count: number of deleted users.
        - users list:
            * filtered by `active` as requested
                - active=True  -> users with isActive truthy
                - active=False -> users that EXPLICITLY have isActive present AND falsy
                - active=None  -> ignore isActive for the list
            * optional `is_deleted` filter for the list (does NOT change counts)
        - deleted_users list: always returned (all deleted users), sorted by createdAt desc.
        """
        logger.info("Entering all_users query")
        try:
            base_projection = {
                "_id": 1,
                "name": 1,
                "email": 1,
                # phone variants
                "phone": 1, "mobile": 1, "contact": 1, "phoneNumber": 1,
                # roles/types
                "usertype": 1, "usertype_id": 1,
                # flags
                "isActive": 1, "isDeleted": 1,
                # timestamps
                "createdAt": 1, "created_at": 1, "updatedAt": 1,
            }

            # Pull ALL users once (both deleted and non-deleted), so we can form all views consistently.
            cursor = users_collection.find({}, projection=base_projection)

            def norm_bool(v) -> bool:
                if isinstance(v, bool): return v
                if isinstance(v, (int, float)): return v == 1
                if isinstance(v, str): return v.strip().lower() in {"true", "1", "yes", "y", "active"}
                return False

            def has_is_active_field(doc: Dict[str, Any]) -> bool:
                # True only if the key exists in the document
                return "isActive" in doc

            def pick_phone(u: dict) -> str:
                return str(u.get("phone") or u.get("mobile") or u.get("contact") or u.get("phoneNumber") or "")

            def stringify_id(v) -> str:
                try:
                    from bson import ObjectId
                    if isinstance(v, ObjectId):
                        return str(v)
                except Exception:
                    pass
                return "" if v is None else str(v)

            def safe_dt(*candidates) -> datetime:
                for x in candidates:
                    if isinstance(x, datetime):
                        return x
                return datetime(1970, 1, 1, tzinfo=timezone.utc)

            def to_user_type(doc: Dict[str, Any]) -> UserType:
                return UserType(
                    id=str(doc.get("_id", "")),
                    name=str(doc.get("name") or ""),
                    email=str(doc.get("email") or ""),
                    phone=pick_phone(doc),
                    usertype_id=stringify_id(doc.get("usertype_id")),
                    usertype=str(doc.get("usertype") or ""),
                    is_active=norm_bool(doc.get("isActive")),
                    is_deleted=norm_bool(doc.get("isDeleted")),
                    created_at=safe_dt(doc.get("createdAt"), doc.get("created_at"), doc.get("updatedAt")),
                )

            # Load & normalize all docs, and also keep flags for presence checks
            all_docs: List[Dict[str, Any]] = []
            async for u in cursor:
                all_docs.append(u)

            all_users_norm: List[UserType] = [to_user_type(d) for d in all_docs]

            # Split deleted / non-deleted
            non_deleted_docs = [d for d in all_docs if not norm_bool(d.get("isDeleted"))]
            deleted_docs = [d for d in all_docs if norm_bool(d.get("isDeleted"))]

            non_deleted_users = [to_user_type(d) for d in non_deleted_docs]
            deleted_users = [to_user_type(d) for d in deleted_docs]

            # --- Counts ---
            total_count = len(non_deleted_users)                              # non-deleted
            active_count = sum(1 for d in non_deleted_docs if norm_bool(d.get("isActive")))  # non-deleted + active
            deleted_count = len(deleted_users)                                # deleted users

            # --- Build the main 'users' list per args ---
            # Start from both sets, then apply is_deleted and active filters
            if is_deleted is True:
                candidate_docs = deleted_docs
            elif is_deleted is False:
                candidate_docs = non_deleted_docs
            else:
                candidate_docs = all_docs  # both

            if active is True:
                # users with isActive truthy (normalize truth)
                candidate_docs = [d for d in candidate_docs if norm_bool(d.get("isActive"))]
            elif active is False:
                # ONLY those that explicitly HAVE the isActive field AND it is falsy
                candidate_docs = [
                    d for d in candidate_docs
                    if has_is_active_field(d) and not norm_bool(d.get("isActive"))
                ]
            # else active is None -> no filter on isActive

            users_list = [to_user_type(d) for d in candidate_docs]

            # Sort lists by created_at desc
            def sort_key(u: UserType):
                return u.created_at if isinstance(u.created_at, datetime) else datetime(MINYEAR, 1, 1)

            users_list.sort(key=sort_key, reverse=True)
            deleted_users.sort(key=sort_key, reverse=True)

            logger.info(
                "all_users: returned=%s | total(non-deleted)=%s | active(non-deleted)=%s | deleted=%s | filters: active=%s is_deleted=%s",
                len(users_list), total_count, active_count, deleted_count, active, is_deleted
            )

            return UserListResponse(
                total_count=total_count,
                active_count=active_count,
                users=users_list,
                deleted_count=deleted_count,
                deleted_users=deleted_users,
            )

        except Exception as e:
            logger.error(f"all_users: MongoDB Error: {str(e)}")
            return UserListResponse(
                total_count=0, active_count=0, users=[], deleted_count=0, deleted_users=[]
            )
        
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
        

    @strawberry.field
    async def get_purchase_data(
        self,
        filter: Optional[PurchaseFilterInput] = None
    ) -> Optional[AdminAnalysisOutput | UserPurchaseOutput | AllPurchaseOutput]:

        query: Dict[str, Any] = {}
        if filter:
            if filter.user_id:
                query["user_id"] = filter.user_id
            if filter.start_date and filter.end_date:
                query["created_at"] = {"$gte": filter.start_date, "$lte": filter.end_date}

        # Pull all first, then organize consistently
        purchases = await purchased_collection.find(query).to_list(None)

        # ------ normalize/defensive defaults + sort purchases by created_at desc ------
        def _safe_dt(x):
            return x if isinstance(x, datetime) else datetime.min

        for p in purchases:
            p.setdefault("courses", [])
            p.setdefault("package_id", None)
            p.setdefault("created_at", None)

            # sort courses by course_id for predictability
            p["courses"] = sorted(
                (p.get("courses") or []),
                key=lambda c: str(c.get("course_id", ""))
            )

        purchases.sort(key=lambda x: _safe_dt(x.get("created_at")), reverse=True)

        # ---------- 1) Admin analytics (ENHANCED + ORGANIZED) ----------
        if filter and filter.admin_analysis:
            total_users = len({p.get("user_id") for p in purchases})
            total_purchases = len(purchases)
            all_courses = [course for p in purchases for course in (p.get("courses") or [])]
            total_courses = len(all_courses)

            completed_courses = sum(
                1 for c in all_courses
                if float(c.get("course_view_percent", 0) or 0) >= 100.0
            )

            # certificate boolean counts
            certificate_sent_true = sum(1 for c in all_courses if bool(c.get("certificate_sent")) is True)
            certificate_sent_false = total_courses - certificate_sent_true

            # Users having any true/false certs
            users_with_true: Set[str] = set()
            users_with_false: Set[str] = set()
            for p in purchases:
                uid = str(p.get("user_id"))
                cs = p.get("courses") or []
                if any(bool(c.get("certificate_sent")) is True for c in cs):
                    users_with_true.add(uid)
                if any(not bool(c.get("certificate_sent", False)) for c in cs):
                    users_with_false.add(uid)

            def _coerce_list_to_ids(id_set: Set[str]) -> List[Any]:
                return [_to_maybe_object_id(s) for s in id_set if s]

            true_ids = _coerce_list_to_ids(users_with_true)
            false_ids = _coerce_list_to_ids(users_with_false)

            certificate_sent_true_users_docs = []
            if true_ids:
                certificate_sent_true_users_docs = await users_collection.find(
                    {"_id": {"$in": true_ids}},
                    projection={
                        "_id": 1, "name": 1, "email": 1, "phone": 1, "mobile": 1,
                        "contact": 1, "phoneNumber": 1, "usertype": 1,
                        "usertype_id": 1, "userTypeId": 1, "user_type_id": 1,
                        "isActive": 1, "isDeleted": 1, "createdAt": 1
                    }
                ).to_list(None)

            certificate_sent_false_users_docs = []
            if false_ids:
                certificate_sent_false_users_docs = await users_collection.find(
                    {"_id": {"$in": false_ids}},
                    projection={
                        "_id": 1, "name": 1, "email": 1, "phone": 1, "mobile": 1,
                        "contact": 1, "phoneNumber": 1, "usertype": 1,
                        "usertype_id": 1, "userTypeId": 1, "user_type_id": 1,
                        "isActive": 1, "isDeleted": 1, "createdAt": 1
                    }
                ).to_list(None)

            # map → GraphQL type
            true_users = [_map_user_doc_to_type(d) for d in certificate_sent_true_users_docs]
            false_users = [_map_user_doc_to_type(d) for d in certificate_sent_false_users_docs]

            def _created_at_safe(u: UserType) -> datetime:
                return u.created_at if isinstance(u.created_at, datetime) else datetime.min

            true_users.sort(key=_created_at_safe, reverse=True)
            false_users.sort(key=_created_at_safe, reverse=True)

            # ---------- Most purchased courses & packages (sorted descending by count) ----------
            course_counter = Counter()
            for c in all_courses:
                cid = c.get("course_id")
                if cid:
                    course_counter[str(cid)] += 1

            package_counter = Counter()
            for p in purchases:
                pid = p.get("package_id")
                if pid:
                    package_counter[str(pid)] += 1

            def _sorted_counter_items(counter: Counter) -> List[Tuple[str, int]]:
                return sorted(counter.items(), key=lambda t: (-t[1], t[0]))

            sorted_courses = _sorted_counter_items(course_counter)
            sorted_packages = _sorted_counter_items(package_counter)

            most_purchased_course = sorted_courses[0][0] if sorted_courses else None
            most_purchased_package = sorted_packages[0][0] if sorted_packages else None

            # Hydrate top single details
            most_purchased_course_details: Optional[CourseDetailsType] = None
            if most_purchased_course:
                cdoc = await courses_collection.find_one({"_id": _to_maybe_object_id(most_purchased_course)})
                if cdoc:
                    most_purchased_course_details = _map_course_doc_to_type(cdoc)

            most_purchased_package_details: Optional[PackageDetailsType] = None
            if most_purchased_package:
                pdoc = await packages_collection.find_one({"_id": _to_maybe_object_id(most_purchased_package)})
                if pdoc:
                    most_purchased_package_details = _map_package_doc_to_type(pdoc)

            # Hydrate full sorted lists
            purchased_courses_details: List[CourseDetailsType] = []
            for cid, count in sorted_courses:
                cdoc = await courses_collection.find_one({"_id": _to_maybe_object_id(cid)})
                if cdoc:
                    ctype = _map_course_doc_to_type(cdoc)
                    setattr(ctype, "purchase_count", count)
                    purchased_courses_details.append(ctype)

            purchased_packages_details: List[PackageDetailsType] = []
            for pid, count in sorted_packages:
                pdoc = await packages_collection.find_one({"_id": _to_maybe_object_id(pid)})
                if pdoc:
                    ptype = _map_package_doc_to_type(pdoc)
                    setattr(ptype, "purchase_count", count)
                    purchased_packages_details.append(ptype)

            return AdminAnalysisOutput(
                total_users=total_users,
                total_purchases=total_purchases,
                total_courses=total_courses,
                completed_courses=completed_courses,
                certificate_sent_true=certificate_sent_true,
                certificate_sent_false=certificate_sent_false,
                certificate_sent_true_users=true_users,
                certificate_sent_false_users=false_users,
                most_purchased_course=most_purchased_course,
                most_purchased_package=most_purchased_package,
                most_purchased_course_details=most_purchased_course_details,
                most_purchased_package_details=most_purchased_package_details,
                all_purchased_courses=purchased_courses_details,
                all_purchased_packages=purchased_packages_details,
            )

        # ---------- 2) User purchases (organized + purchase_id added) ----------
        if filter and filter.user_id:
            user_purchases = [
                PurchaseOutput(
                    purchase_id=str(p.get("_id", "")),  # ✅ Added purchase_id
                    package_id=p.get("package_id"),
                    courses=[
                        CourseOutput(
                            course_id=str(c.get("course_id", "")),
                            course_view_percent=float(c.get("course_view_percent", 0.0) or 0.0),
                            certificate_sent=bool(c.get("certificate_sent", False)),
                        )
                        for c in (p.get("courses") or [])
                    ],
                    created_at=p.get("created_at"),
                )
                for p in purchases
            ]
            return UserPurchaseOutput(user_id=filter.user_id, purchases=user_purchases)

        # ---------- 3) All purchases (organized) ----------
        all_purchases = [
            PurchaseOutput(
                package_id=p.get("package_id"),
                courses=[
                    CourseOutput(
                        course_id=str(c.get("course_id", "")),
                        course_view_percent=float(c.get("course_view_percent", 0.0) or 0.0),
                        certificate_sent=bool(c.get("certificate_sent", False)),
                    )
                    for c in (p.get("courses") or [])
                ],
                created_at=p.get("created_at"),
            )
            for p in purchases
        ]
        return AllPurchaseOutput(all_purchases=all_purchases)


    @strawberry.field(name="allCourses")
    async def all_courses(
        self,
        is_deleted: Optional[bool] = None,     # None -> return all details; True/False -> filter details
        statusCount: Optional[bool] = False,   # if True, compute status counts ONLY on non-deleted
    ) -> CourseListResponse:
        """
        - courses list: respects `is_deleted` filter (None -> all, True -> only deleted, False -> only non-deleted)
        - totalCount: number of NON-DELETED courses
        - statusCounts: histogram of publish status for NON-DELETED courses (only when statusCount=True)
        """
        logger.info("Entering all_courses query")

        try:
            projection = {
                "_id": 1,
                "title": 1, "Title": 1,
                "description": 1, "Description": 1,
                "thumbnail": 1, "Thumbnail": 1,
                "hls": 1, "HLS": 1,
                "language": 1, "Language": 1,
                "desktopAvailable": 1,
                "createdBy": 1, "CreatedBy": 1,
                "creationStage": 1, "CreationStage": 1,
                "publishStatus": 1, "PublishStatus": 1, "status": 1, "Status": 1,
                "isDeleted": 1,
                "deletedBy": 1,
                "deletedAt": 1,
                "createdAt": 1,
                "created_at": 1,
                "updatedAt": 1,
            }

            cursor = courses_collection.find({}, projection=projection)

            def norm_bool(v) -> bool:
                if isinstance(v, bool): return v
                if isinstance(v, (int, float)): return v == 1
                if isinstance(v, str): return v.strip().lower() in {"true","1","yes","y"}
                if v is None: return False
                return False

            def safe_dt(*xs) -> datetime:
                for x in xs:
                    if isinstance(x, datetime):
                        return x
                return datetime(1970, 1, 1, tzinfo=timezone.utc)

            def pick_status(doc: Dict[str, Any]) -> str:
                s = (
                    doc.get("publishStatus")
                    or doc.get("PublishStatus")
                    or doc.get("status")
                    or doc.get("Status")
                    or ""
                )
                s = str(s).strip()
                return s if s else "Unknown"

            def to_course(doc: Dict[str, Any]) -> CourseDetailsType:
                return CourseDetailsType(
                    id=str(doc.get("_id", "")),
                    title=str(doc.get("title") or doc.get("Title") or ""),
                    description=str(doc.get("description") or doc.get("Description") or ""),
                    thumbnail=str(doc.get("thumbnail") or doc.get("Thumbnail") or ""),
                    hls=str(doc.get("hls") or doc.get("HLS") or ""),
                    language=str(doc.get("language") or doc.get("Language") or ""),
                    desktop_available=bool(doc.get("desktopAvailable", True)),
                    created_by=str(doc.get("createdBy") or doc.get("CreatedBy") or ""),
                    creation_stage=str(doc.get("creationStage") or doc.get("CreationStage") or ""),
                    publish_status=pick_status(doc),
                    is_deleted=norm_bool(doc.get("isDeleted")),
                    deleted_by=str(doc.get("deletedBy") or ""),
                    deleted_at=doc.get("deletedAt"),
                    created_at=safe_dt(doc.get("createdAt"), doc.get("created_at"), doc.get("updatedAt")),
                )

            # Normalize all docs
            all_courses_norm: List[CourseDetailsType] = []
            async for c in cursor:
                all_courses_norm.append(to_course(c))

            # Split once
            non_deleted = [x for x in all_courses_norm if not x.is_deleted]
            deleted = [x for x in all_courses_norm if x.is_deleted]

            # === Counts should be from NON-DELETED only ===
            total_count_to_return = len(non_deleted)

            status_counts_list: List[StatusCountType] = []
            if statusCount:
                counter = Counter([x.publish_status for x in non_deleted])
                status_counts_list = [StatusCountType(status=k, count=v) for k, v in counter.items()]

            # courses list respects is_deleted filter (detail payload)
            if is_deleted is True:
                detail_list = deleted
            elif is_deleted is False:
                detail_list = non_deleted
            else:
                detail_list = all_courses_norm

            # Sort details by created_at desc
            def sort_key(x: CourseDetailsType):
                return x.created_at if isinstance(x.created_at, datetime) else datetime(MINYEAR, 1, 1)
            detail_list.sort(key=sort_key, reverse=True)

            logger.info(
                "all_courses: total_non_deleted=%s | deleted=%s | returned_detail=%s | statusCount=%s",
                len(non_deleted), len(deleted), len(detail_list), statusCount
            )

            return CourseListResponse(
                total_count=total_count_to_return,   # <-- ONLY non-deleted
                status_counts=status_counts_list,    # <-- ONLY non-deleted when requested
                courses=detail_list,                 # <-- respects isDeleted arg
            )

        except Exception as e:
            logger.error(f"all_courses: MongoDB Error: {str(e)}")
            return CourseListResponse(total_count=0, status_counts=[], courses=[])


    @strawberry.field(name="getPackageCounts")
    async def get_package_counts(
        self,
        is_deleted: Optional[bool] = None,   # None -> all; True -> only deleted; False -> only non-deleted (detail list)
        statusCount: Optional[bool] = False  # if True, include status histogram computed only on non-deleted
    ) -> PackageCountResponse:
        """
        - total_count / status_counts: computed only on NON-DELETED packages
        - packages (detail list): respects `is_deleted` filter
        - course_details: hydrated from course_ids via courses_collection
        - faqs: mapped to FaqType if shape matches; silently skips malformed items
        - price_details: mapped to your existing PriceType (period, actual_price, price, gst, totalprice)
        """
        try:
            # ---- 1) Pull raw package docs (once) ----
            projection = {
                "_id": 1,
                "title": 1,
                "description": 1,
                "course_ids": 1,
                "status": 1, "Status": 1,
                "isActive": 1,
                "isDeleted": 1,
                "isDraft": 1,
                "createdAt": 1,
                "created_at": 1,
                "updatedAt": 1,
                "createdBy": 1,
                "updatedBy": 1,
                "deletedAt": 1,
                "deletedBy": 1,

                # visuals / extras
                "bannerUrl": 1,
                "themeUrl": 1,
                "banner_base64": 1,  # snake
                "theme_base64": 1,
                "bannerBase64": 1,   # camel variants
                "themeBase64": 1,
                "price_details": 1,
                "telegram_id": 1,
                "faqs": 1,
            }
            pkg_cursor = packages_collection.find({}, projection=projection)
            raw_pkgs: List[Dict[str, Any]] = []
            async for d in pkg_cursor:
                raw_pkgs.append(d)

            # ---- 2) Bulk-load referenced courses (for course_details) ----
            all_course_ids_raw: List[Any] = []
            for d in raw_pkgs:
                ids = d.get("course_ids") or []
                if isinstance(ids, list):
                    all_course_ids_raw.extend(ids)

            from bson import ObjectId
            def to_oid(x):
                if isinstance(x, ObjectId): return x
                if isinstance(x, str):
                    try: return ObjectId(x)
                    except Exception: return x
                return x

            normalized_course_keys = [to_oid(x) for x in all_course_ids_raw]
            unique_oids = list({x for x in normalized_course_keys if isinstance(x, ObjectId)})

            course_proj = {
                "_id": 1,
                "title": 1, "Title": 1,
                "description": 1, "Description": 1,
                "thumbnail": 1, "Thumbnail": 1,
                "hls": 1, "HLS": 1,
                "language": 1, "Language": 1,
                "desktopAvailable": 1,
                "createdBy": 1, "CreatedBy": 1,
                "creationStage": 1, "CreationStage": 1,
                "publishStatus": 1, "PublishStatus": 1, "status": 1, "Status": 1,
                "isDeleted": 1,
                "deletedBy": 1,
                "deletedAt": 1,
                "createdAt": 1,
                "created_at": 1,
                "updatedAt": 1,
            }
            course_map: Dict[str, Dict[str, Any]] = {}
            if unique_oids:
                course_cursor = courses_collection.find({"_id": {"$in": unique_oids}}, projection=course_proj)
                async for cdoc in course_cursor:
                    course_map[str(cdoc["_id"])] = cdoc

            # ---- 3) Helpers ----
            def norm_bool(v) -> bool:
                if isinstance(v, bool): return v
                if isinstance(v, (int, float)): return v == 1
                if isinstance(v, str): return v.strip().lower() in {"true","1","yes","y"}
                return False

            def safe_dt(*xs) -> datetime:
                for x in xs:
                    if isinstance(x, datetime):
                        return x
                return datetime(1970, 1, 1, tzinfo=timezone.utc)

            def clean_str(s: Any) -> str:
                if s is None: return ""
                if not isinstance(s, str): return str(s)
                # remove trailing commas/whitespace your DB shows in screenshots
                return s.strip().rstrip(",")

            def pick_status(doc: Dict[str, Any]) -> str:
                s = (doc.get("status") or doc.get("Status") or "")
                s = clean_str(s)
                return s if s else "Unknown"

            def map_course_doc_to_type(doc: Dict[str, Any]) -> CourseDetailsType:
                ps = (doc.get("publishStatus") or doc.get("PublishStatus") or doc.get("status") or doc.get("Status") or "")
                ps = clean_str(ps) or "Unknown"
                return CourseDetailsType(
                    id=str(doc.get("_id", "")),
                    title=clean_str(doc.get("title") or doc.get("Title") or ""),
                    description=clean_str(doc.get("description") or doc.get("Description") or ""),
                    thumbnail=clean_str(doc.get("thumbnail") or doc.get("Thumbnail") or ""),
                    hls=clean_str(doc.get("hls") or doc.get("HLS") or ""),
                    language=clean_str(doc.get("language") or doc.get("Language") or ""),
                    desktop_available=bool(doc.get("desktopAvailable", True)),
                    created_by=clean_str(doc.get("createdBy") or doc.get("CreatedBy") or ""),
                    creation_stage=clean_str(doc.get("creationStage") or doc.get("CreationStage") or ""),
                    publish_status=ps,
                    is_deleted=norm_bool(doc.get("isDeleted")),
                    deleted_by=clean_str(doc.get("deletedBy") or ""),
                    deleted_at=doc.get("deletedAt"),
                    created_at=safe_dt(doc.get("createdAt"), doc.get("created_at"), doc.get("updatedAt")),
                )

            # Dynamically map faqs to FaqType fields
            def map_faqs(faqs_raw) -> Optional[List['FaqType']]:
                if not faqs_raw:
                    return None
                try:
                    faq_fields = list(FaqType.__annotations__.keys())
                except Exception:
                    return None
                out: List['FaqType'] = []
                for f in faqs_raw:
                    if not isinstance(f, dict):
                        continue
                    data = {k: f.get(k) for k in faq_fields}
                    try:
                        out.append(FaqType(**data))
                    except Exception:
                        continue
                return out or None

            # ✅ Map price_details -> List[PriceType] using YOUR existing PriceType
            # PriceType fields: period(str), actual_price(float), price(float), gst(float), totalprice(float)
            def map_prices(prices_raw) -> Optional[List['PriceType']]:
                if not prices_raw or not isinstance(prices_raw, list):
                    return None

                def to_float(v, default=0.0):
                    if v is None:
                        return default
                    if isinstance(v, (int, float)):
                        return float(v)
                    s = str(v).strip().replace(",", "")
                    try:
                        return float(s)
                    except Exception:
                        return default

                def clean_period(v):
                    return clean_str(v or "")

                out: List['PriceType'] = []
                for p in prices_raw:
                    if not isinstance(p, dict):
                        continue

                    period = clean_period(p.get("period") or p.get("Period"))
                    actual_price = to_float(p.get("actualPrice") or p.get("actual_price"))
                    price = to_float(p.get("price"))
                    gst = to_float(p.get("gst"))
                    # handle multiple variants; your data uses "totalprice"
                    totalprice = to_float(p.get("totalprice") or p.get("totalPrice") or p.get("total_price"))

                    try:
                        out.append(
                            PriceType(
                                period=period,
                                actual_price=actual_price,
                                price=price,
                                gst=gst,
                                totalprice=totalprice,
                            )
                        )
                    except Exception:
                        # skip malformed rows but keep others
                        continue

                return out or None

            # ---- 4) Build PackageDetailsType list (with course_details, faqs, price_details, base64s) ----
            def to_pkg(doc: Dict[str, Any]) -> PackageDetailsType:
                cis_raw = doc.get("course_ids") or []
                cis = [str(x) for x in cis_raw] if isinstance(cis_raw, list) else []

                hydrated_courses: List[CourseDetailsType] = []
                for cid in cis:
                    cdoc = course_map.get(cid)
                    if cdoc:
                        hydrated_courses.append(map_course_doc_to_type(cdoc))

                return PackageDetailsType(
                    id=str(doc.get("_id", "")),
                    title=clean_str(doc.get("title") or ""),
                    description=clean_str(doc.get("description") or ""),
                    course_ids=cis,
                    course_details=hydrated_courses or None,
                    status=pick_status(doc),
                    is_active=bool(doc.get("isActive", False)),
                    is_deleted=norm_bool(doc.get("isDeleted")),
                    is_draft=bool(doc.get("isDraft", False)),
                    created_at=safe_dt(doc.get("createdAt"), doc.get("created_at"), doc.get("updatedAt")),
                    updated_at=doc.get("updatedAt"),
                    created_by=doc.get("createdBy"),
                    updated_by=doc.get("updatedBy"),
                    deleted_at=doc.get("deletedAt"),
                    deleted_by=doc.get("deletedBy"),

                    # visuals
                    banner_url=clean_str(doc.get("bannerUrl") or ""),
                    theme_url=clean_str(doc.get("themeUrl") or ""),
                    banner_base64=clean_str(doc.get("banner_base64") or doc.get("bannerBase64") or ""),
                    theme_base64=clean_str(doc.get("theme_base64") or doc.get("themeBase64") or ""),

                    # business fields
                    price_details=map_prices(doc.get("price_details")),
                    telegram_id=doc.get("telegram_id"),
                    faqs=map_faqs(doc.get("faqs")),
                )

            all_pkgs: List[PackageDetailsType] = [to_pkg(d) for d in raw_pkgs]

            # ---- 5) Non-deleted / Deleted splits, counts, histogram ----
            non_deleted = [p for p in all_pkgs if not p.is_deleted]
            deleted = [p for p in all_pkgs if p.is_deleted]

            total_count = len(non_deleted)

            status_counts: List[PackageStatusCountType] = []
            if statusCount:
                counter = Counter(p.status for p in non_deleted)
                status_counts = [PackageStatusCountType(status=s, count=c) for s, c in counter.items()]

            # ---- 6) Detail list respects is_deleted arg ----
            if is_deleted is True:
                detail_list = deleted
            elif is_deleted is False:
                detail_list = non_deleted
            else:
                detail_list = all_pkgs

            def sort_key(p: PackageDetailsType):
                return p.created_at if isinstance(p.created_at, datetime) else datetime(MINYEAR, 1, 1)
            detail_list.sort(key=sort_key, reverse=True)

            logger.info(
                "get_package_counts: total_non_deleted=%s | deleted=%s | returned_detail=%s | statusCount=%s (hydrated: courses + faqs + prices + base64)",
                len(non_deleted), len(deleted), len(detail_list), statusCount
            )

            return PackageCountResponse(
                total_count=total_count,           # non-deleted only
                status_counts=status_counts,       # non-deleted only (when requested)
                packages=detail_list,              # detail list with course_details, faqs, price_details, base64s
            )

        except Exception as e:
            logger.error(f"get_package_counts: MongoDB Error: {str(e)}")
            return PackageCountResponse(total_count=0, status_counts=[], packages=[])

    @strawberry.field
    async def get_course_progress(
        self, 
        user_id: str, 
        course_id: str
    ) -> Optional[CourseProgressType]: # <-- Type-hint the Strawberry type
        """
        Fetches the complete progress for a user on a specific course,
        including calculated days left.
        """
        print(f"Fetching progress for User {user_id} and Course {course_id}")
        
        progress_doc = await progress_collection.find_one({
            "user_id": user_id,
            "course_id": course_id
        })
        
        if not progress_doc:
            print("❌ Progress document not found.")
            return None
        
        try:
            # --- ⭐️ THIS IS THE KEY ⭐️ ---
            # 1. Load data from DB into the Pydantic model
            progress_model = CourseProgressModel(**progress_doc)
            
            # 2. Return the Pydantic model *directly*.
            # Strawberry will handle the conversion automatically.
            return progress_model 
            
        except Exception as e:
            print(f"❌ Error processing progress document: {e}")
            return None    

    

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
    

    @strawberry.mutation
    async def initialize_course_progress(
        self, 
        user_id: str, 
        course_id: Optional[str] = None,
        package_id: Optional[str] = None,
        expiry: Optional[str] = None  
    ) -> list[CourseProgressType]:
        """
        Initializes course progress for a user.
        Provide EITHER course_id OR package_id.
        """

        if (course_id and package_id) or (not course_id and not package_id):
            raise Exception("Error: You must provide either 'course_id' OR 'package_id', but not both.")

        if package_id and expiry:
            print("ℹ️ User-passed 'expiry' is ignored when 'package_id' is provided (using package expiry).")

        
        new_progress_models = []
        progress_docs_to_insert = []
        
        # --- PATH A: Single Course ---
        if course_id:
            print(f"🔥 Initializing single course progress for User {user_id} on Course {course_id}")
            
            course_expiry_date: Optional[datetime] = None
            if expiry:
                course_expiry_date = parse_period_to_expiry_date(expiry)
                if not course_expiry_date:
                    print(f"⚠️ Could not parse expiry string '{expiry}'. Expiry will be null.")

            try:
                lesson_ids, lesson_durations, course_duration = await fetch_video_lessons_data(course_id)
                
                initial_watch_times = [
                    CourseWatchModel(lesson_id=lid, watch_time=0.0) for lid in lesson_ids
                ]

                new_progress = CourseProgressModel(
                    user_id=user_id,
                    course_id=course_id,
                    lesson_ids=lesson_ids,
                    lesson_duration=lesson_durations,
                    course_duration=course_duration,
                    watch_times=initial_watch_times,
                    total_watch_time=0.0,
                    expiry=course_expiry_date,
                    package_id=None
                )
                
                progress_docs_to_insert.append(new_progress.model_dump(by_alias=True, exclude_none=True))
                new_progress_models.append(new_progress)
                
            except Exception as e:
                print(f"❌ FAILED to process single course {course_id}: {e}.")
                raise Exception(f"Failed to initialize course: {e}")


        # --- PATH B: Package ---
        elif package_id:
            print(f"🔥 Initializing package progress for User {user_id} on Package {package_id}")
            
            package_doc = await packages_collection.find_one({"_id": ObjectId(package_id)})
            if not package_doc:
                raise Exception(f"Package with id={package_id} not found.")
                
            course_ids_in_package = package_doc.get("course_ids", [])
            if not course_ids_in_package:
                raise Exception(f"Package {package_id} contains no course_ids.")
                
            package_expiry_date = None
            try:
                period_str = (package_doc.get("price_details", [{}])[0]).get("period")
                if period_str:
                    package_expiry_date = parse_period_to_expiry_date(period_str)
                    print(f"ℹ️ Package expiry set to: {package_expiry_date} (from '{period_str}')")
            except Exception as e:
                print(f"⚠️ Error parsing package expiry: {e}")
                
            # --- ROBUST LOOP FIX ---
            for cid in course_ids_in_package:
                try:
                    print(f"  -> Processing course {cid} in package...")
                    lesson_ids, lesson_durations, course_duration = await fetch_video_lessons_data(cid)
                    
                    initial_watch_times = [
                        CourseWatchModel(lesson_id=lid, watch_time=0.0) for lid in lesson_ids
                    ]

                    new_progress = CourseProgressModel(
                        user_id=user_id,
                        course_id=cid, 
                        lesson_ids=lesson_ids,
                        lesson_duration=lesson_durations,
                        course_duration=course_duration,
                        watch_times=initial_watch_times,
                        total_watch_time=0.0,
                        expiry=package_expiry_date,
                        package_id=package_id      
                    )
                    progress_docs_to_insert.append(new_progress.model_dump(by_alias=True, exclude_none=True))
                    new_progress_models.append(new_progress)
                    print(f"  ✅ Added course {cid} to be initialized.")

                except Exception as e:
                    # This is the key: if one course fails, log it and continue
                    print(f"  ❌ FAILED to process course {cid}: {e}. Skipping this course.")
                    continue 
            # --- END ROBUST LOOP FIX ---

        # --- 3. Save to MongoDB ---
        if not progress_docs_to_insert:
            print("ℹ️ No progress documents to insert.")
            return []

        try:
            result = await progress_collection.insert_many(progress_docs_to_insert)
            
            inserted_ids = result.inserted_ids
            for model, new_id in zip(new_progress_models, inserted_ids):
                model.id = str(new_id) 
                
            print(f"✅ {len(inserted_ids)} progress document(s) saved.")

            return [CourseProgressType.from_pydantic(model) for model in new_progress_models]

        except Exception as e:
            print(f" Error saving progress to MongoDB: {e}")
            raise Exception(f"Database insertion failed: {e}")
    
    # --- Enhanced Update Function ---

    @strawberry.mutation
    async def update_lesson_watch_time(self, data: LessonWatchTimeInput) -> UpdateWatchTimeResponse:
        print(f"Incoming new_watch_time_seconds: {data.new_watch_time_seconds}")

        # --- Get ID values ---
        user_id_str = data.user_id
        course_id_str = data.course_id
        lesson_id_str = data.lesson_id
        new_watch_time = data.new_watch_time_seconds

        # --- Find Document & Validate Lesson Duration ---
        doc = await progress_collection.find_one({
            "user_id": user_id_str,
            "course_id": course_id_str
        })
        
        if not doc:
            message = f"No document found for user_id/course_id: {user_id_str}, {course_id_str}"
            print(f"❌ {message}")
            return UpdateWatchTimeResponse(success=False, message=message)
            
        print("✅ User/Course document found.")

        # --- LESSON DURATION VALIDATION ---
        try:
            lesson_ids = doc.get("lesson_ids", [])
            lesson_durations = doc.get("lesson_duration", [])

            try:
                lesson_index = lesson_ids.index(lesson_id_str)
            except ValueError:
                message = f"Lesson ID {lesson_id_str} not found in lesson_ids array."
                print(f"❌ {message}")
                return UpdateWatchTimeResponse(success=False, message=message)

            if lesson_index >= len(lesson_durations):
                message = "Data mismatch: lesson_ids and lesson_duration arrays have different lengths."
                print(f"❌ {message}")
                return UpdateWatchTimeResponse(success=False, message=message)
                
            max_duration = lesson_durations[lesson_index]

            # This is the validation you asked for:
            if new_watch_time > max_duration:
                message = f"VALIDATION FAILED: New watch time ({new_watch_time}) exceeds lesson duration ({max_duration})."
                print(f"❌ {message}")
                return UpdateWatchTimeResponse(success=False, message=message)
            
            print(f"✅ Lesson validation passed: New time {new_watch_time} <= max duration {max_duration}.")

        except Exception as e:
            message = f"Error during validation: {e}"
            print(f"❌ {message}")
            return UpdateWatchTimeResponse(success=False, message=str(e))
        # --- END LESSON VALIDATION ---

        # --- Pipeline ---
        pipeline = [
            # Stage 1: Update the specific lesson's watch time
            {
                "$set": {
                    "watch_times": {
                        "$map": {
                            "input": {"$ifNull": ["$watch_times", []]},
                            "as": "lesson",
                            "in": {
                                "$mergeObjects": [
                                    "$$lesson",
                                    {
                                        "$cond": {
                                            "if": {"$eq": ["$$lesson.lesson_id", lesson_id_str]},
                                            "then": {
                                                "watch_time": {
                                                    "$max": [
                                                        new_watch_time,
                                                        {"$ifNull": ["$$lesson.watch_time", 0]}
                                                    ]
                                                }
                                            },
                                            "else": {}
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            # Stage 2: Recalculate and CLAMP the top-level 'total_watch_time'
            {
                "$set": {
                    "total_watch_time": {
                        "$min": [
                            {
                                "$sum": {
                                    "$map": {
                                        "input": "$watch_times",
                                        "as": "lesson",
                                        "in": {"$ifNull": ["$$lesson.watch_time", 0]}
                                    }
                                }
                            },
                            {"$ifNull": ["$course_duration", 100000000]}
                        ]
                    }
                }
            }
        ]

        # --- Run update ---
        try:
            result = await progress_collection.update_one(
                {
                    "user_id": user_id_str,
                    "course_id": course_id_str
                },
                pipeline,
            )
            
            print("Matched:", result.matched_count, "Modified:", result.modified_count)
            
            if result.matched_count == 1:
                return UpdateWatchTimeResponse(success=True, message="Update successful")
            else:
                message = "Update failed: Document not found during update operation."
                print(f" {message}")
                return UpdateWatchTimeResponse(success=False, message=message)
            
        except Exception as e:
            message = f"Error updating watch time: {e}"
            print(f" {message}")
            return UpdateWatchTimeResponse(success=False, message=str(e))


# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)