# downloader.py
# Small helper to run yt-dlp per-file with isolated progress state.
from pathlib import Path
from typing import Dict, Optional, Sequence

import requests
import yt_dlp
from tqdm import tqdm
from yt_dlp.utils import json

from models import Lesson
from utils import load_secret


class YTDLDownloader:
    def __init__(
        self,
        lesson_data: Lesson,
        out_dir: Path,
        use_aria2: bool = False,
        aria2_args: Optional[Sequence[str]] = None,
    ):
        self.out_dir = out_dir
        self.file_stem = f"{lesson_data.index:02d}_{lesson_data.name}"
        self.use_aria2 = use_aria2
        self.aria2_args = aria2_args or ["-x", "16", "-s", "16", "-j", "16", "-k", "1M", "--summary-interval=0"]

        # progress bar kept per instance
        self._pbar: Optional[tqdm] = None

        self._cookies, self._headers = load_secret()
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _progress_hook(self, d: dict):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)

            if self._pbar is None:
                # create bar for this file
                filename = d.get("filename") or f"{self.file_stem}.mp4"
                short_name = Path(filename).stem[:60]
                self._pbar = tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1000,  # show MB/s not MiB/s
                    desc=f"{short_name}",
                    leave=False,
                )

            # update bar
            if total:
                self._pbar.total = total
            self._pbar.n = downloaded
            self._pbar.refresh()

        elif status == "finished":
            # merging finished
            if self._pbar is not None:
                # ensure it reaches total
                if self._pbar.total and self._pbar.n < self._pbar.total:
                    self._pbar.n = self._pbar.total
                self._pbar.refresh()
                self._pbar.close()
                self._pbar.clear()
                self._pbar = None

            # brief confirmation
            print(f"✅ {d.get('filename', self.file_stem)} done.")

        elif status == "error":
            if self._pbar is not None:
                self._pbar.close()
                self._pbar.clear()
                self._pbar = None
            print("❌ yt-dlp error:", d)

    def _build_opts(self) -> dict:
        """Build options for yt-dlp."""
        output_file_path = self.out_dir / f"{self.file_stem}.%(ext)s"

        opts = {
            "outtmpl": str(output_file_path.resolve()),
            "quiet": True,
            "noprogress": True,  # don't show yt-dlp built-in progress bar
            "merge_output_format": "mp4",  # merge segments into a single file
            "progress_hooks": [self._progress_hook],
            "no_warnings": True,  # don't show yt-dlp warnings
            "logtostderr": False,  # don't show yt-dlp logs to stderr
            "ratelimit": None,
            "throttledratelimit": None,
            "retries": 10,
            "fragment_retries": 10,
            # allow yt-dlp to use its internal concurrent fragment downloader as fallback
            "concurrent_fragment_downloads": 4,
        }

        if self.use_aria2:
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

        return opts

    def _save_file(self, url: str, save_file_path: Path, show_progress: bool = True, is_binary: bool = True) -> None:
        """Download a file from a URL with optional progress bar."""
        mode = "wb" if is_binary else "w"

        # Ensure parent directory exists
        save_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Make streaming request
            response = requests.get(
                url,
                headers=self._headers,
                cookies=self._cookies,
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

    def _save_reading_material(self, reading_material_id: str, save_file_path: Path) -> None:
        """Download and save reading material."""
        params = {
            "batch": "1",
            "input": json.dumps({"0": {"json": {"materialId": reading_material_id}}}),
        }

        response = requests.get(
            "https://learn.deeplearning.ai/api/trpc/course.getReadingMaterial",
            params=params,
            cookies=self._cookies,
            headers=self._headers,
        )
        response.raise_for_status()

        data = response.json()
        with open(save_file_path, "w", encoding="utf-8") as f:
            f.write(data[0]["result"]["data"]["json"]["content"])

    def _extract_video_and_caption_urls(self, video_id: int) -> Dict[str, str]:
        """Extract video and caption URLs from the API."""
        params = {
            "batch": "1",
            "input": json.dumps({"0": {"json": {"videoId": video_id}}}),
        }

        response = requests.get(
            "https://learn.deeplearning.ai/api/trpc/course.getLessonVideo",
            params=params,
            cookies=self._cookies,
            headers=self._headers,
        )

        if not response.ok:
            return {}

        data = response.json()[0]["result"]["data"]["json"]["video"]
        caption_url = data["tracks"][0]["src"]
        video_url = data["mp4Url"] if data["mp4Url"] else data["webmUrl"]

        return {"caption_url": caption_url, "video_url": video_url}

    def download_video_from_m3u8(self, m3u8_url: str) -> None:
        """Download a video from a m3u8 URL and save it to the output directory."""
        opts = self._build_opts()
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([m3u8_url])

    def download_lesson_content(self, lesson_data: Lesson) -> Lesson:
        """
        Download a single lesson (reading material or video).

        This method is designed to be called concurrently.

        Args:
            lesson_data: The lesson data object
        """
        lesson_type = lesson_data.type

        if lesson_type == "reading_material" and lesson_data.readingMaterialId:
            self._save_reading_material(
                lesson_data.readingMaterialId,
                self.out_dir / f"{self.file_stem}.md",
            )
        elif lesson_type in ("video", "video_notebook") and lesson_data.videoId:
            lesson_video_data = self._extract_video_and_caption_urls(lesson_data.videoId)
            if lesson_video_data.get("caption_url"):
                # Download caption first (smaller, faster)
                self._save_file(
                    lesson_video_data["caption_url"],
                    self.out_dir / f"{self.file_stem}.vtt",
                    is_binary=True,
                    show_progress=False,  # Hide individual file progress in concurrent mode
                )
            if lesson_video_data.get("video_url"):
                # Then download video (larger, slower)
                self.download_video_from_m3u8(lesson_video_data["video_url"])

        return lesson_data
