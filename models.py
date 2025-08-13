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
from typing import Optional
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

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        # NEW: Exclude fields with None values when dumping the model
        exclude_none = True


# --- New Model for Package Creation ---

class PackageModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    title: str
    description: Optional[str] = None
    banner_url: Optional[str] = Field(default=None, alias="bannerUrl")
    theme_url: Optional[str] = Field(default=None, alias="themeUrl")
    is_active: bool = Field(default=True, alias="isActive")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    # ✅ NEW: Add the created_by field
    # created_by: Optional[ObjectId] = Field(default=None, alias="createdBy")
    created_by: Optional[str] = Field(default=None, alias="createdBy")
    updated_by: Optional[ObjectId] = Field(default=None, alias="updated_by")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        exclude_none = True