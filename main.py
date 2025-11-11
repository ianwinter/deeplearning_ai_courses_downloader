"""
DeepLearning.AI Course Downloader

This module provides functionality to download courses from DeepLearning.AI.
Use the Course class for the main functionality.
"""

from pathlib import Path

from course import Course


def main():
    """Main entry point for the script."""
    # Example 1: Download using URL
    # course_url = "https://learn.deeplearning.ai/courses/pydantic-for-llm-workflows/lesson/w6ohb/welcome-to-pydantic-for-llm-workflows"
    course_url = "https://learn.deeplearning.ai/courses/getting-structured-llm-output"
    course = Course.build_from_url(course_url)
    print(f"Found course: {course}")
    root_dir = Path("/home/work/Tutorials/DeepLearning.AI")
    save_dir = root_dir / course.slug
    course.download(save_dir, concurrent_downloads=2)

    # Example 2: Download using slug directly
    # course = Course.build_from_url("large-language-models-semantic-search")
    # course.download(Path("./courses/llm-semantic-search"))

    # Example 3: If you already have the course data dict
    # course_data = {...}
    # course = Course(course_data)
    # course.download(Path("./my-course"))


if __name__ == "__main__":
    main()
