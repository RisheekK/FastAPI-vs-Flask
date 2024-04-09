# Shared Pydantic models for request and response data
from pydantic import BaseModel, EmailStr, validator


class ContactBase(BaseModel):
    username: str
    phonenumber: int
    country: str | None = None
    state: str | None = None
    email: EmailStr
    email_opt_in_status: bool
    phonenumber_opt_in_status: bool

    @validator('username')
    def validate_username_length(cls, value):
        """Ensures username is not null and has a minimum length."""
        if not value:
            raise ValueError("username cannot be null")
        if len(value) < 3:
            raise ValueError("username must be at least 3 characters long")
        return value

    @validator('phonenumber')
    def validate_phonenumber_range(cls, value):
        """Validates phone number format (optional, adjust as needed)."""
        if not isinstance(value, int) or len(str(value)) != 10 or not (1 <= value <= 9999999999):
            raise ValueError("phonenumber must be a valid 10-digit integer")
        return value


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ContactBase):
    id: int  # Required for update