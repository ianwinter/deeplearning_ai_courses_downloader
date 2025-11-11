import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
import yt_dlp
from pydantic import BaseModel, field_validator
from tqdm import tqdm

from utils import load_secret

COOKIES, HEADERS = load_secret()
COURSES_BASE_URL = "https://learn.deeplearning.ai/courses/"
PLATFORM_API = "https://platform-api.dlai.link"


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


class Course:
    """
    Course class for downloading DeepLearning.AI courses.

    Examples:
        # Create from dict
        course_data = {...}
        course = Course(course_data)
        course.download(save_dir=Path("./courses"))

        # Create from URL/slug
        course = Course.build_from_url("https://learn.deeplearning.ai/courses/...")
        course.download(save_dir=Path("./courses"))
    """

    def __init__(self, course_data: Dict[str, Any]):
        """
        Initialize Course from a dictionary.

        Args:
            course_data: Dictionary containing 'lessons' and 'course_info' keys.

        Raises:
            ValidationError: If course_data doesn't match the expected schema.
        """
        # Validate and parse the course data using Pydantic
        self._data = CourseData(**course_data)

    @classmethod
    def build_from_url(cls, course_url_or_slug: str) -> "Course":
        """
        Build a Course instance by fetching data from a course URL or slug.

        Args:
            course_url_or_slug: Either a full course URL or just the slug.

        Returns:
            Course instance with fetched data.

        Raises:
            ValueError: If the course ID/slug is invalid.
            requests.RequestException: If the API request fails.
        """
        course_slug = cls._extract_course_slug(course_url_or_slug)
        raw_data = cls._fetch_raw_data(course_slug)
        return cls.build_from_raw_data(raw_data)

    @classmethod
    def build_from_raw_data(cls, raw_data: Dict[str, Any]) -> "Course":
        """
        Build a Course instance from raw API response data.

        Args:
            raw_data: Raw course data dict with 'name', 'slug', 'lessons', 'wpData', etc.

        Returns:
            Course instance
        """
        final_data = {
            "lessons": raw_data["lessons"],
            "course_info": {
                "name": raw_data["name"],
                "slug": raw_data["slug"],
                "type": raw_data["type"],
                "courseId": raw_data["courseId"],
                "releasedAt": datetime.fromisoformat(raw_data["releasedAt"]).strftime("%d %B %Y"),
                "coursePartner": raw_data["wpData"]["coursePartner"],
                "courseTopic": raw_data["wpData"]["courseTopic"],
                "courseLevel": raw_data["wpData"]["courseLevel"],
                "courseThumbnail": raw_data["wpData"]["videoThumbnail"],
            },
        }

        return cls(final_data)

    @staticmethod
    def _extract_course_slug(course_id: str) -> str:
        """Extract course slug from URL or return slug as-is."""
        if course_id is None:
            raise ValueError("Course id is required")

        course_slug = course_id.strip()
        if course_slug.startswith(COURSES_BASE_URL):
            course_slug = course_slug[len(COURSES_BASE_URL) :].split("/")[0]

        return course_slug

    @staticmethod
    def _fetch_raw_data(course_slug: str) -> Dict[str, Any]:
        """Fetch course data from the API."""
        params = {
            "batch": "1",
            "input": json.dumps({"0": {"json": {"courseSlug": course_slug}}}),
        }

        response = requests.get(
            "https://learn.deeplearning.ai/api/trpc/course.getCourseBySlug",
            params=params,
            cookies=COOKIES,
            headers=HEADERS,
        )
        response.raise_for_status()

        data = response.json()[0]["result"]["data"]["json"]
        return data

    def download(self, save_dir: Path) -> None:
        """
        Download the entire course including videos, captions, and reading materials.

        Args:
            save_dir: Directory where the course will be saved.
        """
        print("Getting course content list...")
        course_info = self._data.course_info
        lessons = self._data.lessons

        if not lessons:
            print(f"No lessons found for course {course_info.slug}")
            return

        print("Saving course info...")
        save_dir.mkdir(parents=True, exist_ok=True)
        self._save_course_info_as_markdown(save_dir / "00_course_info.md")

        print("Downloading course lessons...")
        with tqdm(
            total=len(lessons),
            desc=f"Downloading Course: {course_info.slug}",
            leave=True,
        ) as pbar:
            for index, (lesson_id, lesson_data) in enumerate(lessons.items(), start=1):
                name = lesson_data.name
                lesson_type = lesson_data.type

                if lesson_type == "reading_material" and lesson_data.readingMaterialId:
                    self._save_reading_material(
                        lesson_data.readingMaterialId,
                        save_dir / f"{index:02d}_{name}.md",
                    )
                elif lesson_type in ("video", "video_notebook") and lesson_data.videoId:
                    video_data = self._extract_video_and_caption_urls(lesson_data.videoId)
                    if video_data:
                        self._save_file(
                            video_data["caption_url"],
                            save_dir / f"{index:02d}_{name}.vtt",
                            is_binary=True,
                        )
                        self._download_video_from_m3u8(
                            video_data["video_url"],
                            save_dir,
                            f"{index:02d}_{name}",
                            use_aria2c=False,
                        )
                pbar.update(1)
                pbar.refresh()

        print(f"\nCourse downloaded successfully to: {save_dir}")

    def _save_course_info_as_markdown(self, save_file_path: Path) -> None:
        """Save course information as a markdown file."""
        course_info = self._data.course_info
        lessons = self._data.lessons

        # Ensure parent directory exists
        save_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Build markdown content
        md_lines = []

        # Course header with thumbnail
        md_lines.append(f"# {course_info.name}\n")

        if course_info.courseThumbnail:
            md_lines.append(f"![Course Thumbnail]({course_info.courseThumbnail})\n")

        md_lines.append("---\n")

        # Course metadata
        md_lines.append("## Course Information\n\n")

        if course_info.slug:
            course_url = f"{COURSES_BASE_URL}{course_info.slug}"
            md_lines.append(f"- **Course Link**: [{course_info.name}]({course_url})\n")

        md_lines.append(f"- **Course ID**: `{course_info.courseId}`\n")
        md_lines.append(f"- **Type**: {course_info.type.replace('_', ' ').title()}\n")
        md_lines.append(f"- **Released**: {course_info.releasedAt}\n")

        if course_info.coursePartner:
            partners = []
            for partner in course_info.coursePartner:
                if isinstance(partner, CoursePartner):
                    if partner.logo:
                        partners.append(f"{partner.title}\n![{partner.title}]({partner.logo})")
                    else:
                        partners.append(partner.title)
            md_lines.append(f"- **Partner**: {' | '.join(partners)}\n")

        md_lines.append(f"- **Level**: {course_info.courseLevel}\n")

        if course_info.courseTopic:
            topics_str = ", ".join(course_info.courseTopic)
            md_lines.append(f"- **Topics**: {topics_str}\n")

        md_lines.append("\n---\n")

        # Lessons section
        md_lines.append("## Lessons\n\n")

        # Sort lessons by index
        sorted_lessons = sorted(lessons.items(), key=lambda x: x[1].index if x[1] else 0)

        for lesson_id, lesson_data in sorted_lessons:
            lesson_index = lesson_data.index
            lesson_name = lesson_data.name
            lesson_type = lesson_data.type
            lesson_slug = lesson_data.slug
            lesson_time = lesson_data.time or 0

            # Format time
            time_str = ""
            if lesson_time:
                minutes = lesson_time // 60
                seconds = lesson_time % 60
                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
                else:
                    time_str = f"{seconds}s"

            # Build lesson link
            lesson_url = f"{COURSES_BASE_URL}{course_info.slug}/lesson/{lesson_slug}/{lesson_name.replace(' ', '-')}"

            # Lesson type emoji/icon
            type_icon = {
                "video": "🎥",
                "video_notebook": "🎥",
                "reading_material": "📄",
                "quiz": "❓",
                "program": "💻",
                "chatbot": "💬",
            }.get(lesson_type, "📌")

            # Format lesson entry
            md_lines.append(f"### {lesson_index}. {type_icon} {lesson_name}\n\n")
            md_lines.append(f"- **Type**: {lesson_type.replace('_', ' ').title()}\n")

            if time_str:
                md_lines.append(f"- **Duration**: {time_str}\n")

            md_lines.append(f"- **Link**: [{lesson_name}]({lesson_url})\n")

            # Additional info based on lesson type
            if lesson_type == "video" and lesson_data.videoId:
                md_lines.append(f"- **Video ID**: `{lesson_data.videoId}`\n")

            if lesson_type == "reading_material" and lesson_data.readingMaterialId:
                md_lines.append(f"- **Reading Material ID**: `{lesson_data.readingMaterialId}`\n")

            if lesson_type == "quiz" and lesson_data.quizId:
                md_lines.append(f"- **Quiz ID**: `{lesson_data.quizId}`\n")

            md_lines.append("\n")

        # Write to file
        with open(save_file_path, "w", encoding="utf-8") as f:
            f.write("".join(md_lines))

    def _save_reading_material(self, reading_material_id: str, save_file_path: Path) -> None:
        """Download and save reading material."""
        params = {
            "batch": "1",
            "input": json.dumps({"0": {"json": {"materialId": reading_material_id}}}),
        }

        response = requests.get(
            "https://learn.deeplearning.ai/api/trpc/course.getReadingMaterial",
            params=params,
            cookies=COOKIES,
            headers=HEADERS,
        )
        response.raise_for_status()

        data = response.json()
        with open(save_file_path, "w", encoding="utf-8") as f:
            f.write(data[0]["result"]["data"]["json"]["content"])

    def _save_file(self, url: str, save_file_path: Path, show_progress: bool = True, is_binary: bool = True) -> None:
        """Download a file from a URL with optional progress bar."""
        mode = "wb" if is_binary else "w"

        # Ensure parent directory exists
        save_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Make streaming request
            response = requests.get(
                url,
                headers=HEADERS,
                cookies=COOKIES,
                stream=True,
                timeout=30,
                allow_redirects=True,
            )
            response.raise_for_status()

            # Get file size from headers if available
            total_size = int(response.headers.get("content-length", 0)) or None

            if show_progress:
                # Download with progress bar (disappears when done with leave=False)
                with (
                    open(save_file_path, mode) as f,
                    tqdm(
                        desc=save_file_path.name,
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        leave=False,  # Progress bar disappears when done
                    ) as pbar,
                ):
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                # Download without progress bar, just print log line
                print(f"Downloading {save_file_path.name}...", end=" ", flush=True)
                with open(save_file_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print("Done")

        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error saving file {save_file_path}: {e}")
            raise

    def _download_video_from_m3u8(self, m3u8_url: str, out_dir: Path, file_stem: str, use_aria2c: bool = False) -> None:
        """Download video from m3u8 url and save it as MP4."""
        out_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = out_dir / f"{file_stem}.%(ext)s"

        opts = {
            "outtmpl": str(outtmpl.resolve()),
            "quiet": True,
            "merge_output_format": "mp4",  # merge segments into a single file
            "noprogress": False,  # don't show yt-dlp built-in progress bar
            "no_warnings": True,  # don't show yt-dlp warnings
            "logtostderr": False,  # don't show yt-dlp logs to stderr
            "ratelimit": None,
            "throttledratelimit": None,
            "retries": 10,
            "fragment_retries": 10,
        }

        if use_aria2c:
            opts.update(
                {
                    "external_downloader": "aria2c",
                    "external_downloader_args": [
                        "-x",
                        "16",  # max connections per server
                        "-s",
                        "16",  # split into N segments
                        "-j",
                        "16",  # parallel downloads
                        "-k",
                        "1M",  # segment size
                        "--summary-interval=0",
                    ],
                }
            )

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([m3u8_url])

    def _extract_video_and_caption_urls(self, video_id: int) -> Dict[str, str]:
        """Extract video and caption URLs from the API."""
        params = {
            "batch": "1",
            "input": json.dumps({"0": {"json": {"videoId": video_id}}}),
        }

        response = requests.get(
            "https://learn.deeplearning.ai/api/trpc/course.getLessonVideo",
            params=params,
            cookies=COOKIES,
            headers=HEADERS,
        )

        if not response.ok:
            return {}

        data = response.json()[0]["result"]["data"]["json"]["video"]
        caption_url = data["tracks"][0]["src"]
        video_url = data["mp4Url"] if data["mp4Url"] else data["webmUrl"]

        return {"caption_url": caption_url, "video_url": video_url}

    @property
    def name(self) -> str:
        """Get course name."""
        return self._data.course_info.name

    @property
    def slug(self) -> str:
        """Get course slug."""
        return self._data.course_info.slug

    @property
    def lesson_count(self) -> int:
        """Get number of lessons."""
        return len(self._data.lessons)

    def __repr__(self) -> str:
        """String representation of the course."""
        return f"Course(name='{self.name}', slug='{self.slug}', lessons={self.lesson_count})"
