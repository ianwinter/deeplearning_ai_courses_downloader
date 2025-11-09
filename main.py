import json
from datetime import datetime
from pathlib import Path

import requests
import yt_dlp
from tqdm import tqdm

from utils import load_secret

COOKIES, HEADERS = load_secret()
COURSES_BASE_URL = "https://learn.deeplearning.ai/courses/"
PLATFORM_API = "https://platform-api.dlai.link"


def extract_course_slug(course_id: str) -> str:
    if course_id is None:
        raise ValueError("Course id is required")

    course_slug = course_id.strip()
    if course_slug.startswith(COURSES_BASE_URL):
        course_slug = course_slug[len(COURSES_BASE_URL) :].split("/")[0]

    return course_slug


def get_content_list_by_course_id(course_id: str) -> dict:
    global COOKIES, HEADERS

    course_slug = extract_course_slug(course_id)
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

    data = response.json()[0]["result"]["data"]

    final_data = {
        "lessons": data["json"]["lessons"],
        "course_info": {
            "name": data["json"]["name"],
            "slug": data["json"]["slug"],
            "type": data["json"]["type"],
            "courseId": data["json"]["courseId"],
            "releasedAt": datetime.fromisoformat(data["json"]["releasedAt"]).strftime("%d %B %Y"),
            "coursePartner": data["json"]["wpData"]["coursePartner"],
            "courseTopic": data["json"]["wpData"]["courseTopic"],
            "courseLevel": data["json"]["wpData"]["courseLevel"],
            "courseThumbnail": data["json"]["wpData"]["videoThumbnail"],
        },
    }

    return final_data


def save_course_info_as_markdown(course_data: dict, save_file_path: Path):
    """
    Save course information as a well-formatted markdown file.

    Args:
        course_data: Full dict returned from get_content_list_by_course_id()
                    with 'lessons' and 'course_info' keys
        save_file_path: Path where the markdown file should be saved
    """
    if not course_data:
        print("No course data provided")
        return

    course_info = course_data.get("course_info", {})
    lessons = course_data.get("lessons", {})

    # Ensure parent directory exists
    save_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Build markdown content
    md_lines = []

    # Course header with thumbnail
    course_name = course_info.get("name", "Unknown Course")
    course_thumbnail = course_info.get("courseThumbnail", "")

    md_lines.append(f"# {course_name}\n")

    if course_thumbnail:
        md_lines.append(f"![Course Thumbnail]({course_thumbnail})\n")

    md_lines.append("---\n")

    # Course metadata
    md_lines.append("## Course Information\n\n")

    course_slug = course_info.get("slug", "")
    if course_slug:
        course_url = f"{COURSES_BASE_URL}{course_slug}"
        md_lines.append(f"- **Course Link**: [{course_name}]({course_url})\n")

    course_id = course_info.get("courseId")
    if course_id:
        md_lines.append(f"- **Course ID**: `{course_id}`\n")

    course_type = course_info.get("type", "")
    if course_type:
        md_lines.append(f"- **Type**: {course_type.replace('_', ' ').title()}\n")

    released_at = course_info.get("releasedAt", "")
    if released_at:
        md_lines.append(f"- **Released**: {released_at}\n")

    course_partner = course_info.get("coursePartner", [])
    if course_partner:
        partners = []
        for partner in course_partner if isinstance(course_partner, list) else [course_partner]:
            partner_title = partner.get("title", "") if isinstance(partner, dict) else str(partner)
            partner_logo = partner.get("logo", "") if isinstance(partner, dict) else ""
            if partner_logo:
                partners.append(f"{partner_title}\n![{partner_title}]({partner_logo})")
            else:
                partners.append(partner_title)
        md_lines.append(f"- **Partner**: {' | '.join(partners)}\n")

    course_level = course_info.get("courseLevel", "")
    if course_level:
        md_lines.append(f"- **Level**: {course_level}\n")

    course_topics = course_info.get("courseTopic", [])
    if course_topics:
        topics_str = ", ".join(course_topics) if isinstance(course_topics, list) else str(course_topics)
        md_lines.append(f"- **Topics**: {topics_str}\n")

    md_lines.append("\n---\n")

    # Lessons section
    md_lines.append("## Lessons\n\n")

    # Sort lessons by index
    sorted_lessons = sorted(lessons.items(), key=lambda x: x[1].get("index", 0) if isinstance(x[1], dict) else 0)

    for lesson_id, lesson_data in sorted_lessons:
        if not isinstance(lesson_data, dict):
            continue

        lesson_index = lesson_data.get("index", 0)
        lesson_name = lesson_data.get("name", "Unnamed Lesson")
        lesson_type = lesson_data.get("type", "unknown")
        lesson_slug = lesson_data.get("slug", lesson_id)
        lesson_time = lesson_data.get("time", 0)

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
        lesson_url = f"{COURSES_BASE_URL}{course_slug}/lesson/{lesson_slug}/{lesson_name.replace(' ', '-')}"

        # Lesson type emoji/icon
        type_icon = {
            "video": "🎥",
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
        if lesson_type == "video" and lesson_data.get("videoId"):
            md_lines.append(f"- **Video ID**: `{lesson_data.get('videoId')}`\n")

        if lesson_type == "reading_material" and lesson_data.get("readingMaterialId"):
            md_lines.append(f"- **Reading Material ID**: `{lesson_data.get('readingMaterialId')}`\n")

        if lesson_type == "quiz" and lesson_data.get("quizId"):
            md_lines.append(f"- **Quiz ID**: `{lesson_data.get('quizId')}`\n")

        md_lines.append("\n")

    # Write to file
    with open(save_file_path, "w", encoding="utf-8") as f:
        f.write("".join(md_lines))


def extract_video_and_caption_urls(video_id: int) -> dict | None:
    """Extract video and caption URLs from platform-api."""
    url = f"{PLATFORM_API}/videos/{video_id}/caption.json?v=None"
    try:
        r = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=10)
        if not r.ok:
            return None
        json_response = r.json()
        caption_url = json_response.get("data", {}).get("subtitleUrl")
        if not caption_url:
            raise ValueError("Caption URL not found in response")

        # "https://dyckms5inbsqq.cloudfront.net/Anthropic/C3/L6/subtitle/eng/sc-Anthropic-C3-L6.vtt"
        # "https://dyckms5inbsqq.cloudfront.net/Anthropic/C3/L6/video/1080/sc-Anthropic-C3-L6.m3u8"
        video_file_name = Path(caption_url).stem + ".m3u8"
        base_url = caption_url.split("/subtitle/")[0]
        video_url = f"{base_url}/video/1080/{video_file_name}"
        return {"caption_url": caption_url, "video_url": video_url}

    except Exception:
        print(f"Error trying platform-api video {video_id}")
        return None


def save_reading_material(readingMaterialId: str, save_file_path: Path):
    params = {
        "batch": "1",
        "input": json.dumps({"0": {"json": {"materialId": readingMaterialId}}}),
    }

    # "queryHash": "[[\"course\",\"getReadingMaterial\"],{\"input\":{\"materialId\":\"01K20J2YYR3MS8KM01HSTE64PD\"},\"type\":\"query\"}]"
    response = requests.get(
        "https://learn.deeplearning.ai/api/trpc/course.getReadingMaterial",
        params=params,
        cookies=COOKIES,
        headers=HEADERS,
    )

    data = response.json()
    with open(save_file_path, "w") as f:
        f.write(data[0]["result"]["data"]["json"]["content"])


def save_file(url: str, save_file_path: Path, show_progress: bool = True, is_binary: bool = True):
    """
    Download a file from a URL with optional progress bar.

    Args:
        url: URL of the file to download
        save_file_path: Path where the file should be saved
        show_progress: If True, show tqdm progress bar (disappears when done).
                      If False, only print a log line.
        is_binary: If True, save the file as binary.
                  If False, save the file as text.
    """
    if is_binary:
        mode = "wb"
    else:
        mode = "w"

    # Ensure parent directory exists
    save_file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Make streaming request
        response = requests.get(url, headers=HEADERS, cookies=COOKIES, stream=True, timeout=30, allow_redirects=True)

        # Check if request was successful
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


def progress_hook(d):
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes", 0)
        if not hasattr(progress_hook, "bar"):
            filename = d.get("filename", "")
            if filename:
                filename = Path(filename).stem[:50] + "..."
            description = f"Downloading {filename}"
            progress_hook.bar = tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=description,
                # leave=False,  # removes the bar once done
            )
        progress_hook.bar.total = total or progress_hook.bar.total
        progress_hook.bar.n = downloaded
        progress_hook.bar.refresh()
    elif d["status"] == "finished":
        if hasattr(progress_hook, "bar"):
            progress_hook.bar.refresh()
            progress_hook.bar.n = progress_hook.bar.total
            progress_hook.bar.close()
            # progress_hook.bar.clear()  # erase the line once done


def download_video_from_m3u8(m3u8_url: str, out_dir: Path, file_stem: str, use_aria2c=False):
    """
    Download video from m3u8 url and save it as MP4 to the output directory with the given file stem.

    Args:
        m3u8_url (str): The url of the m3u8 file.
        out_dir (Path): The directory to save the video.
        file_stem (str): The stem of the video file.
        use_aria2c (bool, optional): Use aria2c for downloading. Defaults to False.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = out_dir / f"{file_stem}.%(ext)s"

    opts = {
        "outtmpl": str(outtmpl.resolve()),
        "quiet": True,
        # "progress_hooks": [progress_hook],  # use tqdm progress bar
        "merge_output_format": "mp4",  # merge segments into a single file
        "noprogress": False,  # don't show yt-dlp built-in progress bar
        "no_warnings": True,  # don't show yt-dlp warnings
        "logtostderr": False,  # don't show yt-dlp logs to stderr
        # "ratelimit": None,
        # "throttledratelimit": None,
        # "retries": 10,
        # "fragment_retries": 10,
        # "nopart": True,
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


def download_course_by_id(course_slug: str, save_dir: Path):
    """Download course by slug."""

    print("Getting course content list...")
    data = get_content_list_by_course_id(course_slug)
    course_list = data.get("lessons", {})

    if not course_list:
        print(f"No lessons found for course {course_slug}")
        return

    print("Saving course info...")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_course_info_as_markdown(data, save_dir / "00_course_info.md")

    with tqdm(total=len(course_list), desc=f"Downloading Course: {course_slug}", leave=True) as pbar:
        for index, (lesson_id, lesson_data) in enumerate(course_list.items(), start=1):
            name = lesson_data.get("name")
            lesson_type = lesson_data.get("type")

            if lesson_type == "reading_material":
                save_reading_material(lesson_data.get("readingMaterialId"), save_dir / f"{index:02d}_{name}.md")
            elif lesson_type == "video":
                video_data = extract_video_and_caption_urls(lesson_data.get("videoId"))
                if video_data:
                    print("video_data: ", video_data)
                    save_file(video_data["caption_url"], save_dir / f"{index:02d}_{name}.vtt", is_binary=True)
                    download_video_from_m3u8(video_data["video_url"], save_dir, f"{index:02d}_{name}", use_aria2c=False)
            pbar.update(1)
            pbar.refresh()


def main():
    # course_url = "https://learn.deeplearning.ai/courses/claude-code-a-highly-agentic-coding-assistant/lesson/hhfj3/prompts-&-summaries-of-lessons"
    course_url = "https://learn.deeplearning.ai/courses/large-language-models-semantic-search/lesson/vq7qi/introduction"
    course_slug = extract_course_slug(course_url)
    save_dir = Path(__file__).parent / "courses" / course_slug
    download_course_by_id(course_slug, save_dir)


if __name__ == "__main__":
    main()
