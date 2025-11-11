"""
DeepLearning.AI Course Downloader

This module provides functionality to download courses from DeepLearning.AI.
Use the Course class for the main functionality.
"""

import argparse
import sys
import time
from pathlib import Path

from tqdm import tqdm

from course import Course
from user import User


def prepare_args():
    parser = argparse.ArgumentParser(
        description="Download courses from DeepLearning.AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
    # Download a single course using full URL
    python main.py "https://learn.deeplearning.ai/courses/my-course-slug"

    # Download a single course using just the slug
    python main.py my-course-slug

    # Download enrolled courses (studying only)
    python main.py --enrolled studying

    # Download enrolled courses (finished only)
    python main.py --enrolled finished

    # Download all enrolled courses (studying + finished)
    python main.py --enrolled all

    # Specify output directory
    python main.py my-course-slug --output-dir ./my-courses

    # Download with concurrent downloads (faster)
    python main.py my-course-slug --concurrent 3

    # Combine options
    python main.py --enrolled all -o ./downloads -c 2
        """,
    )

    parser.add_argument(
        "course",
        type=str,
        nargs="?",
        help=(
            "Course URL or slug (e.g., 'my-course-slug' or "
            "'https://learn.deeplearning.ai/courses/my-course-slug'). "
            "Required if --enrolled is not used."
        ),
    )

    parser.add_argument(
        "-e",
        "--enrolled",
        type=str,
        choices=["studying", "finished", "all"],
        help=(
            "Download enrolled courses. Choose 'studying', 'finished', or 'all'. "
            "If specified, course argument is not needed."
        ),
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="./courses",
        help="Directory where courses will be saved (default: ./courses)",
    )

    parser.add_argument(
        "-c",
        "--concurrent",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Number of lessons to download concurrently (default: 1). "
            "Higher values can speed up downloads but may hit rate limits."
        ),
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.course and not args.enrolled:
        parser.error("Either 'course' argument or '--enrolled' option must be provided")

    if args.course and args.enrolled:
        parser.error("Cannot specify both 'course' argument and '--enrolled' option")

    if args.concurrent < 1:
        parser.error("--concurrent must be at least 1")

    return args


def download_enrolled_courses(args: argparse.Namespace, output_dir: Path):
    # Download enrolled courses
    user = User()
    courses_data = []

    if args.enrolled == "studying":
        tqdm.write("Fetching studying courses...")
        courses_data = user.list_studying_courses()
        status_name = "studying"
    elif args.enrolled == "finished":
        tqdm.write("Fetching finished courses...")
        courses_data = user.list_finished_courses()
        status_name = "finished"
    elif args.enrolled == "all":
        tqdm.write("Fetching all enrolled courses...")
        courses_data = user.list_all_courses()
        status_name = "enrolled"

    if not courses_data:
        tqdm.write("No enrolled courses found.")
        return

    tqdm.write(f"Found {len(courses_data)} {status_name} course(s)\n")

    # Download each course
    for idx, course_data in enumerate(courses_data, 1):
        course_slug = course_data.get("slug")
        course_name = course_data.get("name", "Unknown")

        if not course_slug:
            tqdm.write(f"Skipping course {idx}: No slug found")
            continue

        tqdm.write(f"[{idx}/{len(courses_data)}] Processing: {course_name}")
        tqdm.write(f"  Slug: {course_slug}")

        try:
            # Build course from raw data
            course = Course.build_from_raw_data(course_data)
            tqdm.write(f"  Lessons: {course.lesson_count}")

            # Determine save directory
            save_dir = output_dir / course.slug

            # Download the course
            tqdm.write(f"  Saving to: {save_dir}\n")
            course.download(save_dir, concurrent_downloads=args.concurrent)

        except Exception as e:
            tqdm.write(f"  ✗ Error downloading {course_name}: {e}\n")

        # Sleep 1 minute between courses (except after the last one)
        if idx < len(courses_data):
            tqdm.write("  Waiting 60 seconds before next course...\n")
            time.sleep(60)

    tqdm.write(f"✅ All {len(courses_data)} course(s) processed!")


def download_single_course(args: argparse.Namespace, output_dir: Path):
    # Download single course
    course_url_or_slug = args.course.strip()

    # Build course from URL or slug
    tqdm.write(f"Loading course: {course_url_or_slug}")
    course = Course.build_from_url(course_url_or_slug)
    tqdm.write(f"Found course: {course.name}")
    tqdm.write(f"  Slug: {course.slug}")
    tqdm.write(f"  Lessons: {course.lesson_count}")

    # Determine save directory
    save_dir = output_dir / course.slug

    # Download the course
    tqdm.write(f"\nSaving to: {save_dir}")
    course.download(save_dir, concurrent_downloads=args.concurrent)


def main():
    """Main entry point for the CLI script."""

    args = prepare_args()

    # Convert output directory to Path
    output_dir = Path(args.output_dir).expanduser().resolve()

    try:
        if args.enrolled:
            download_enrolled_courses(args, output_dir)
        else:
            download_single_course(args, output_dir)

    except KeyboardInterrupt:
        tqdm.write("\n\nDownload interrupted by user.")
        sys.exit(1)
    except Exception as e:
        tqdm.write(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
