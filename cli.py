"""
DeepLearning.AI Course Downloader

This module provides functionality to download courses and specializations from DeepLearning.AI.
Use the Course class for the main functionality.
"""

import argparse
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm

from auth import SUPPORTED_BROWSERS, create_session
from course import Course
from user import User


def prepare_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download courses and specializations from DeepLearning.AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download a single course using full URL
  dl-ai "https://learn.deeplearning.ai/courses/my-course-slug"

  # Download a single course using just the slug
  dl-ai my-course-slug

  # Download a full specialization bundle
  dl-ai -s generative-ai-for-software-development

  # Download enrolled courses (studying only)
  dl-ai --enrolled studying

  # Download enrolled courses (finished only)
  dl-ai --enrolled finished

  # Download all enrolled courses (studying + finished)
  dl-ai --enrolled all

  # Specify output directory
  dl-ai my-course-slug --output-dir ./my-courses

  # Download with concurrent downloads (faster)
  dl-ai my-course-slug --concurrent 3

  # Combine options
  dl-ai --enrolled all -o ./downloads -c 2
        """,
    )

    parser.add_argument(
        "course",
        type=str,
        nargs="?",
        help=(
            "Course URL or slug (e.g., 'my-course-slug' or "
            "'https://learn.deeplearning.ai/courses/my-course-slug'). "
            "Required if --enrolled or --specialization is not used."
        ),
    )

    parser.add_argument(
        "-s",
        "--specialization",
        type=str,
        metavar="SLUG",
        help="Specialization URL or slug. Downloads all sub-courses within the specialization bundle.",
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

    parser.add_argument(
        "-b",
        "--browser",
        type=str,
        choices=SUPPORTED_BROWSERS,
        default="chrome",
        help=(
            f"Browser to extract cookies from (default: chrome). Supported browsers: {', '.join(SUPPORTED_BROWSERS)}"
        ),
    )

    args = parser.parse_args()

    # Validate arguments: ensure exactly one target mode is specified
    targets = [bool(args.course), bool(args.enrolled), bool(args.specialization)]

    if sum(targets) == 0:
        parser.error("Must specify 'course' argument, '--enrolled', or '--specialization'")
    elif sum(targets) > 1:
        parser.error("Cannot combine 'course', '--enrolled', and '--specialization' options")

    return args


def download_enrolled_courses(args: argparse.Namespace, output_dir: Path, session: requests.Session) -> None:
    """Download user's enrolled courses based on filter criteria."""
    user = User(session)
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

    for idx, course_data in enumerate(courses_data, 1):
        course_slug = course_data.get("slug")
        course_name = course_data.get("name", "Unknown")

        if not course_slug:
            tqdm.write(f"Skipping course {idx}: No slug found")
            continue

        tqdm.write(f"[{idx}/{len(courses_data)}] Processing: {course_name}")
        tqdm.write(f"  Slug: {course_slug}")

        try:
            course = Course.build_from_raw_data(course_data, session)
            tqdm.write(f"  Lessons: {course.lesson_count}")

            save_dir = output_dir / course.slug
            tqdm.write(f"  Saving to: {save_dir}\n")
            course.download(save_dir, concurrent_downloads=args.concurrent)

        except Exception as e:
            tqdm.write(f"  ✗ Error downloading {course_name}: {e}\n")

        if idx < len(courses_data):
            tqdm.write("  Waiting 60 seconds before next course...\n")
            time.sleep(60)

    tqdm.write(f"✅ All {len(courses_data)} course(s) processed!")


def download_single_course(args: argparse.Namespace, output_dir: Path, session: requests.Session) -> None:
    """Download a single standalone course."""
    course_url_or_slug = args.course.strip()

    tqdm.write(f"Loading course: {course_url_or_slug}")
    course = Course.build_from_url(course_url_or_slug, session=session)
    tqdm.write(f"Found course: {course.name}")
    tqdm.write(f"  Slug: {course.slug}")
    tqdm.write(f"  Lessons: {course.lesson_count}")

    save_dir = output_dir / course.slug
    tqdm.write(f"\nSaving to: {save_dir}")
    course.download(save_dir, concurrent_downloads=args.concurrent)


def download_specialization(args: argparse.Namespace, output_dir: Path, session: requests.Session) -> None:
    """Download all sub-courses within a specialization bundle."""
    spec_slug = Course._extract_course_slug(args.specialization.strip())

    tqdm.write(f"Fetching specialization info for: {spec_slug}...")

    try:
        sub_slugs = Course.fetch_specialization_course_slugs(spec_slug, session)
    except Exception as e:
        tqdm.write(f"❌ Failed to fetch specialization '{spec_slug}': {e}", file=sys.stderr)
        return

    if not sub_slugs:
        tqdm.write(f"❌ No courses found for specialization '{spec_slug}'")
        return

    tqdm.write(f"Found Specialization '{spec_slug}' containing {len(sub_slugs)} sub-course(s):\n")

    spec_dir = output_dir / spec_slug

    for idx, sub_slug in enumerate(sub_slugs, 1):
        tqdm.write(f"[{idx}/{len(sub_slugs)}] Processing course: {sub_slug}")
        try:
            course = Course.build_from_url(sub_slug, session=session)
            tqdm.write(f"  Name: {course.name}")
            tqdm.write(f"  Lessons: {course.lesson_count}")

            save_dir = spec_dir / course.slug
            tqdm.write(f"  Saving to: {save_dir}\n")

            course.download(save_dir, concurrent_downloads=args.concurrent)

        except Exception as e:
            tqdm.write(f"  ✗ Error downloading sub-course '{sub_slug}': {e}\n")

        if idx < len(sub_slugs):
            tqdm.write("  Waiting 5 seconds before next course...\n")
            time.sleep(5)

    tqdm.write(f"✅ Finished processing specialization '{spec_slug}'!")


def main() -> None:
    """Main entry point for the CLI script."""
    args = prepare_args()

    try:
        tqdm.write(f"Extracting cookies from {args.browser}...")
        session = create_session(browser=args.browser)
        tqdm.write(f"✅ Successfully authenticated using {args.browser} cookies\n")
    except Exception as e:
        tqdm.write(f"❌ Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir).expanduser().resolve()

    try:
        if args.enrolled:
            download_enrolled_courses(args, output_dir, session)
        elif args.specialization:
            download_specialization(args, output_dir, session)
        else:
            download_single_course(args, output_dir, session)

    except KeyboardInterrupt:
        tqdm.write("\n\nDownload interrupted by user.")
        sys.exit(1)
    except Exception as e:
        tqdm.write(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
