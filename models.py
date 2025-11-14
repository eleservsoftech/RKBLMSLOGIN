from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List
from bson import ObjectId

# --- Database Models (Pydantic) ---

# Corresponds to your Mongoose userTypeSchema
class UserTypeModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        # NEW: Exclude fields with None values when dumping the model
        exclude_none = True

# Corresponds to your Mongoose userSchema
class UserModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str
    email: EmailStr
    phone: str
    password: str # We will store the hashed password here
    usertype_id: ObjectId # Corresponds to a Mongoose.Schema.Types.ObjectId
    usertype: Optional[str] = None  
    is_active: bool = Field(default=True, alias="isActive")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    deleted_at: Optional[datetime] = Field(default=None, alias="deleted_at")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="created_at")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        # NEW: Exclude fields with None values when dumping the model
        exclude_none = True

# Corresponds to your Mongoose loginSchema
class LoginModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: ObjectId # Corresponds to a Mongoose.Schema.Types.ObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    token: Optional[str] = None  # <-- NEW: Field to store the JWT token

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        # NEW: Exclude fields with None values when dumping the model
        exclude_none = True

# NEW: Pydantic model for FAQ items
class FaqModel(BaseModel):
    question: str
    answer: str

class PriceModel(BaseModel):
    period: str
    actual_price: float = Field(alias="actualPrice") # Add alias for camelCase
    price: float
    gst: float
    totalprice:float
 # Add the Config class to your PriceModel
    class Config:
        populate_by_name = True
class PackageModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = Field(alias="thumbnailUrl", default=None)
    banner_url: Optional[str] = Field(alias="bannerUrl", default=None)
    theme_url: Optional[str] = Field(alias="themeUrl", default=None)
    is_active: bool = Field(default=True, alias="isActive")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    created_by: Optional[str] = Field(default=None, alias="createdBy")
    updated_by: Optional[str] = Field(default=None, alias="updatedBy")
    course_ids: Optional[List[str]] = Field(default_factory=list, alias="course_ids")
    # REMOVED: This is no longer used for a single price
    # price: Optional[float] = None
    
    # NEW: A list of PriceModel objects to handle multiple pricing tiers
    price_details: Optional[List[PriceModel]] = Field(default=None, alias="price_details")
    
    telegram_id: Optional[List[str]] = Field(default=None)
    # CORRECTED: Use FaqModel instead of a generic dict
    faqs: Optional[List[FaqModel]] = None
    is_draft: bool = Field(default=False, alias="isDraft")
    status: Optional[str] = None  # NEW: Field to save the package status


    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        exclude_none = True

# --- Course progress (one course) ---
class CourseProgressModel(BaseModel):
    course_id: str
    course_view_percent: float = 0.0  # default 0%
    certificate_sent: bool = False  # Added per course

class PurchasedModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    name: str
    email: EmailStr
    phone: str
    package_id: Optional[str] = None  # None if single course
    courses: List[CourseProgressModel]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)



class CourseWatchModel(BaseModel):
    lesson_id: str
    watch_time: float  # in seconds or minutes (based on your logic)

# class CourseProgressModel(BaseModel):
#     id: Optional[str] = Field(alias="_id", default=None)
#     user_id: str
#     course_id: str
#     lesson_ids: List[str]  # array of lesson IDs
#     lesson_duration: list[float]  # total duration of all lessons (in minutes or seconds)
#     course_duration: float  # total duration of the course
#     watch_times: List[CourseWatchModel]  # array of lessons with watch times
#     total_watch_time: float  # total watched time (sum of watch_times)
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     updated_at: datetime = Field(default_factory=datetime.utcnow)


# class CourseProgressModel(BaseModel):
#     id: Optional[str] = Field(alias="_id", default=None)
#     user_id: str
#     course_id: str
    
#     # --- New Optional Fields ---
#     package_id: Optional[str] = None  # To track which package this was from
#     expiry: Optional[datetime] = None # The expiry date for this course access
    
#     # --- Existing Fields ---
#     lesson_ids: List[str]      # array of lesson IDs
#     lesson_duration: list[float]  # total duration of all lessons
#     course_duration: float     # total duration of the course
#     watch_times: List[CourseWatchModel]  # array of lessons with watch times
#     total_watch_time: float    # total watched time (sum of watch_times)
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     updated_at: datetime = Field(default_factory=datetime.utcnow)


class CourseProgressModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    course_id: str
    package_id: Optional[str] = None
    expiry: Optional[datetime] = None
    lesson_ids: List[str]
    lesson_duration: list[float]
    course_duration: float
    watch_times: List[CourseWatchModel]
    total_watch_time: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # --- ⭐️ ADD THIS VALIDATOR ⭐️ ---
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        """Converts the MongoDB _id (ObjectId) to a string."""
        if isinstance(v, ObjectId):
            return str(v)
        return v

    class Config:
        # This tells Pydantic to allow the 'id' field to be
        # populated by the '_id' alias when loading from a dict.
        populate_by_name = True