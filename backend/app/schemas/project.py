from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.enums import ProjectStatus, ProjectType
from app.schemas.user import UserSummary


class AcademicProjectBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    academic_year: str = Field(..., min_length=4, max_length=20, pattern=r"^\d{4}(-\d{4})?$")
    semester: int = Field(..., ge=1, le=12)
    department: str = Field(..., min_length=2, max_length=100)
    project_type: ProjectType = ProjectType.CAPSTONE
    status: ProjectStatus = ProjectStatus.PLANNING
    start_date: date
    target_deadline: date

    @model_validator(mode="after")
    def validate_date_range(self) -> "AcademicProjectBase":
        if self.target_deadline < self.start_date:
            raise ValueError("target_deadline cannot be earlier than start_date")
        return self


class AcademicProjectCreate(AcademicProjectBase):
    faculty_guide_id: Optional[UUID] = None


class FacultyGuideAssignRequest(BaseModel):
    faculty_guide_id: UUID


class AcademicProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    academic_year: Optional[str] = Field(None, min_length=4, max_length=20, pattern=r"^\d{4}(-\d{4})?$")
    semester: Optional[int] = Field(None, ge=1, le=12)
    department: Optional[str] = Field(None, min_length=2, max_length=100)
    project_type: Optional[ProjectType] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[date] = None
    target_deadline: Optional[date] = None
    actual_completion_date: Optional[date] = None
    faculty_guide_id: Optional[UUID] = None

    @model_validator(mode="after")
    def validate_update_dates(self) -> "AcademicProjectUpdate":
        if self.start_date and self.target_deadline:
            if self.target_deadline < self.start_date:
                raise ValueError("target_deadline cannot be earlier than start_date")
        return self


class AcademicProjectRead(AcademicProjectBase):
    id: UUID
    owner_id: UUID
    faculty_guide_id: Optional[UUID] = None
    actual_completion_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserSummary] = None
    faculty_guide: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)


class AcademicProjectSummary(BaseModel):
    id: UUID
    title: str
    academic_year: str
    semester: int
    department: str
    project_type: ProjectType
    status: ProjectStatus
    start_date: date
    target_deadline: date

    model_config = ConfigDict(from_attributes=True)
