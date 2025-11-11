from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, field_validator


class CoursePartner(BaseModel):
    """Model for course partner information."""

    title: str
    logo: Optional[str] = None


class CourseInfo(BaseModel):
    """Model for course metadata."""

    name: str
    slug: str
    type: str
    courseId: int
    releasedAt: str
    coursePartner: List[Union[CoursePartner, Dict[str, Any]]]
    courseTopic: List[str]
    courseLevel: str
    courseThumbnail: str

    @field_validator("coursePartner", mode="before")
    @classmethod
    def validate_course_partner(cls, v):
        """Convert dict partners to CoursePartner objects."""
        if isinstance(v, list):
            result = []
            for partner in v:
                if isinstance(partner, dict):
                    result.append(CoursePartner(**partner))
                else:
                    result.append(partner)
            return result
        return v


class Lesson(BaseModel):
    """Model for a lesson."""

    index: int
    slug: str
    name: str
    type: str
    videoId: Optional[int] = None
    time: Optional[int] = None
    programId: Optional[Union[str, int]] = None
    chatbotId: Optional[Union[str, int]] = None
    iframeUrl: Optional[str] = None
    quizId: Optional[str] = None
    progress: Optional[int] = None
    readingMaterialId: Optional[str] = None
    accessControl: Optional[str] = None
    requiredUserTier: Optional[str] = None
    features: Optional[Dict[str, Any]] = None


class CourseData(BaseModel):
    """Model for complete course data."""

    lessons: Dict[str, Lesson]
    course_info: CourseInfo

    @field_validator("lessons", mode="before")
    @classmethod
    def validate_lessons(cls, v):
        """Convert dict lessons to Lesson objects."""
        if isinstance(v, dict):
            result = {}
            for key, lesson in v.items():
                if isinstance(lesson, dict):
                    result[key] = Lesson(**lesson)
                else:
                    result[key] = lesson
            return result
        return v
