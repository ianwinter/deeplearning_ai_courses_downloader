import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

import requests
from tqdm import tqdm

from downloader import YTDLDownloader
from models import CourseData, CoursePartner
from urls import DeepLearningAIURLs

# Thread-safe lock for progress bar updates
_pbar_lock = Lock()


class Course:
    """
    Course class for downloading DeepLearning.AI courses.

    Examples:
        # Create from dict
        course_data = {...}
        course = Course(course_data, session)
        course.download(save_dir=Path("./courses"))

        # Create from URL/slug
        course = Course.build_from_url("https://learn.deeplearning.ai/courses/...", session)
        course.download(save_dir=Path("./courses"))
    """

    def __init__(self, course_data: Dict[str, Any], session: requests.Session):
        """
        Initialize Course from a dictionary.

        Args:
            course_data: Dictionary containing 'lessons' and 'course_info' keys.
            session: Configured requests.Session instance with cookies and headers.

        Raises:
            pydantic.ValidationError: If course_data doesn't match the expected schema.
        """
        # Validate and parse the course data using Pydantic
        self._data = CourseData(**course_data)
        self.session = session

    @classmethod
    def build_from_url(cls, course_url_or_slug: str, session: requests.Session) -> "Course":
        """Build a Course instance by fetching data from a course URL or slug."""
        course_slug = cls._extract_course_slug(course_url_or_slug)
        raw_data = cls._fetch_raw_data(course_slug, session)
        return cls.build_from_raw_data(raw_data, session)

    @classmethod
    def build_from_raw_data(cls, raw_data: dict, session: requests.Session) -> "Course":
        """Construct a Course instance from raw tRPC JSON data."""
        # 1. Normalize lessons to a dictionary (as expected by CourseData Pydantic model)
        raw_lessons = raw_data.get("lessons") or {}
        if isinstance(raw_lessons, list):
            lessons_dict = {str(item.get("id", i)): item for i, item in enumerate(raw_lessons)}
        elif isinstance(raw_lessons, dict):
            lessons_dict = raw_lessons
        else:
            lessons_dict = {}

        # 2. Extract and sanitize course_info (wpData or raw_data)
        course_info = dict(raw_data.get("wpData") or raw_data)

        # 3. Supply safe fallback values matching CourseData schema types
        defaults = {
            "coursePartner": [],
            "courseTopic": [],
            "courseLevel": "Intermediate",
            "courseThumbnail": "",
        }
        for key, val in defaults.items():
            if key not in course_info or course_info[key] is None:
                course_info[key] = val

        # 4. Construct payload matching CourseData schema
        course_payload = {
            "course_info": course_info,
            "lessons": lessons_dict,
        }

        return cls(course_data=course_payload, session=session)

    @classmethod
    def fetch_specialization_course_slugs(cls, specialization_slug: str, session: requests.Session) -> List[str]:
        """
        Fetch sub-course slugs for a given specialization slug.

        Args:
            specialization_slug: Slug identifier for the specialization.
            session: Configured requests.Session instance.

        Returns:
            List of sub-course slug strings.
        """
        params = {
            "batch": "1",
            "input": json.dumps({"0": {"json": {"specializationSlug": specialization_slug}}}),
        }

        response = session.get(
            DeepLearningAIURLs.GET_SPECIALIZATION,
            params=params,
        )
        response.raise_for_status()

        res_data = response.json()
        if not res_data or not isinstance(res_data, list):
            return []

        data = res_data[0].get("result", {}).get("data", {}).get("json", {})
        courses = data.get("courses", [])

        return [c["slug"] for c in courses if isinstance(c, dict) and "slug" in c]

    @staticmethod
    def _extract_course_slug(course_id: str) -> str:
        """Extract course slug from URL or return slug as-is."""
        if course_id is None:
            raise ValueError("Course id is required")

        course_slug = course_id.strip()
        if course_slug.startswith(DeepLearningAIURLs.COURSES_BASE):
            course_slug = course_slug[len(DeepLearningAIURLs.COURSES_BASE) + 1 :].split("/")[0]

        return course_slug

    @staticmethod
    def _fetch_raw_data(course_slug: str, session: requests.Session) -> Dict[str, Any]:
        """
        Fetch course data from the API.

        Args:
            course_slug: Course slug identifier
            session: Configured requests.Session instance with cookies and headers

        Returns:
            Dictionary containing course data
        """
        params = {
            "batch": "1",
            "input": json.dumps({"0": {"json": {"courseSlug": course_slug}}}),
        }

        response = session.get(
            DeepLearningAIURLs.GET_COURSE_BY_SLUG,
            params=params,
        )
        response.raise_for_status()

        data = response.json()[0]["result"]["data"]["json"]
        return data

    def download(self, save_dir: Path, concurrent_downloads: int = 1) -> None:
        """
        Download the entire course including videos, captions, and reading materials.

        Args:
            save_dir: Directory where the course will be saved.
            concurrent_downloads: Number of lessons to download in parallel (default: 1).
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

        # Sort lessons by index to maintain order
        sorted_lessons = sorted(lessons.items(), key=lambda x: x[1].index if x[1] else 0)

        print(f"Downloading {len(sorted_lessons)} lessons (concurrent: {concurrent_downloads})...")

        # Create progress bar at position 0 (outer bar)
        pbar = tqdm(
            total=len(sorted_lessons),
            desc=f"Downloading Course: {course_info.slug}",
            leave=True,
            position=0,
        )

        # Download lessons
        if concurrent_downloads == 1:
            for index, (lesson_id, lesson_data) in enumerate(sorted_lessons, start=1):
                downloader = YTDLDownloader(lesson_data, save_dir, self.session, position=1)
                success = downloader.download_lesson_content(lesson_data)
                if not success:
                    tqdm.write(f"Error downloading lesson {index} ({lesson_data.name})")
                else:
                    pbar.update(1)
        else:
            with ThreadPoolExecutor(max_workers=concurrent_downloads) as executor:
                future_to_lesson = {}
                for idx, (lesson_id, lesson_data) in enumerate(sorted_lessons):
                    slot = 1 + (idx % concurrent_downloads)
                    downloader = YTDLDownloader(lesson_data, save_dir, self.session, position=slot)
                    future = executor.submit(downloader.download_lesson_content, lesson_data)
                    future_to_lesson[future] = lesson_data

                for future in as_completed(future_to_lesson):
                    lesson_data = future_to_lesson[future]
                    try:
                        success = future.result()
                        if success:
                            pbar.update(1)
                    except Exception as e:
                        tqdm.write(f"Error downloading lesson {lesson_data.index} ({lesson_data.name}): {e}")

        pbar.close()
        tqdm.write(f"\nCourse downloaded successfully to: '{save_dir}'")

    def _save_course_info_as_markdown(self, save_file_path: Path) -> None:
        """Save course information as a markdown file."""
        course_info = self._data.course_info
        lessons = self._data.lessons

        save_file_path.parent.mkdir(parents=True, exist_ok=True)

        md_lines = []
        md_lines.append(f"# {course_info.name}\n")

        if course_info.courseThumbnail:
            md_lines.append(f"![Course Thumbnail]({course_info.courseThumbnail})\n")

        md_lines.append("---\n")
        md_lines.append("## Course Information\n\n")

        if course_info.slug:
            course_url = f"{DeepLearningAIURLs.COURSES_BASE}/{course_info.slug}"
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
        md_lines.append("## Lessons\n\n")

        sorted_lessons = sorted(lessons.items(), key=lambda x: x[1].index if x[1] else 0)

        for lesson_id, lesson_data in sorted_lessons:
            lesson_index = lesson_data.index
            lesson_name = lesson_data.name
            lesson_type = lesson_data.type
            lesson_slug = lesson_data.slug
            lesson_time = lesson_data.time or 0

            time_str = ""
            if lesson_time:
                minutes = lesson_time // 60
                seconds = lesson_time % 60
                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
                else:
                    time_str = f"{seconds}s"

            lesson_url = "{base}/{slug}/lesson/{lesson_slug}/{lesson_name}".format(
                base=DeepLearningAIURLs.COURSES_BASE,
                slug=course_info.slug,
                lesson_slug=lesson_slug,
                lesson_name=lesson_name.replace(" ", "-"),
            )

            type_icon = {
                "video": "🎥",
                "video_notebook": "🎥",
                "reading_material": "📄",
                "quiz": "❓",
                "program": "💻",
                "chatbot": "💬",
            }.get(lesson_type, "📌")

            md_lines.append(f"### {lesson_index}. {type_icon} {lesson_name}\n\n")
            md_lines.append(f"- **Type**: {lesson_type.replace('_', ' ').title()}\n")

            if time_str:
                md_lines.append(f"- **Duration**: {time_str}\n")

            md_lines.append(f"- **Link**: [{lesson_name}]({lesson_url})\n")

            if lesson_type == "video" and lesson_data.videoId:
                md_lines.append(f"- **Video ID**: `{lesson_data.videoId}`\n")

            if lesson_type == "reading_material" and lesson_data.readingMaterialId:
                md_lines.append(f"- **Reading Material ID**: `{lesson_data.readingMaterialId}`\n")

            if lesson_type == "quiz" and lesson_data.quizId:
                md_lines.append(f"- **Quiz ID**: `{lesson_data.quizId}`\n")

            md_lines.append("\n")

        with open(save_file_path, "w", encoding="utf-8") as f:
            f.write("".join(md_lines))

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
