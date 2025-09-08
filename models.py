# models.py
# Libraries to install:
# pip install pydantic "pydantic[email]"

from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional
from bson import ObjectId

# --- Database Models (Pydantic) ---

# models.py
# Libraries to install:
# pip install pydantic "pydantic[email]"

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
    price: Optional[float] = None
    telegram_id: Optional[List[str]] = Field(default=None)
    # CORRECTED: Use FaqModel instead of a generic dict
    faqs: Optional[List[FaqModel]] = None
    is_draft: bool = Field(default=False, alias="isDraft")


    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        exclude_none = True

