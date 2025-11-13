"""
URL constants for DeepLearning.AI Course Downloader.

This module contains all URLs used throughout the application.
"""

from enum import Enum


class DeepLearningAIURLs(str, Enum):
    """Enumeration of all DeepLearning.AI URLs used in the application."""

    # Base URLs
    BASE = "https://learn.deeplearning.ai"
    COURSES_BASE = "https://learn.deeplearning.ai/courses"
    API_BASE_URL = "https://learn.deeplearning.ai/api/trpc"

    # API Endpoints
    ENROLLED_CURRICULUMS_V2 = API_BASE_URL + "/course.enrolledCurriculumsV2"
    GET_COURSE_BY_SLUG = API_BASE_URL + "/course.getCourseBySlug"
    GET_READING_MATERIAL = API_BASE_URL + "/course.getReadingMaterial"
    GET_LESSON_VIDEO = API_BASE_URL + "/course.getLessonVideo"

    def __str__(self) -> str:
        """Return the URL value as a string."""
        return self.value
