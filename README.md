# DeepLearning.AI Course Downloader

A Python CLI tool to download courses and full specializations from DeepLearning.AI, including videos, captions, and reading materials.

## Installation

### From Source

```bash
# Clone the repository
git clone [https://github.com/karimelgazar/deeplearning_ai_courses_downloader](https://github.com/karimelgazar/deeplearning_ai_courses_downloader)
cd deeplearning_ai_courses_downloader

# Install in editable mode (recommended)
pip install -e .

# Make sure it's installed
dl-ai -h
```

### As a `uv` tool

```bash
# Install uv if it is not already installed
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/karimelgazar/deeplearning_ai_courses_downloader
cd deeplearning_ai_courses_downloader

# Install as an editable tool using uv
uv tool install --editable .

# Make sure it's installed
dl-ai -h
```

## Configuration

The tool automatically extracts authentication cookies from your browser. **Make sure you are logged into DeepLearning.AI in your browser** before running the downloader.

Supported browsers:
- Chrome
- Chromium
- Opera
- Opera GX
- Brave
- Edge
- Vivaldi
- Firefox
- LibreWolf
- Safari

## Usage

### Download a Single Course

```bash
# Using full URL
dl-ai "[https://learn.deeplearning.ai/courses/my-course-slug](https://learn.deeplearning.ai/courses/my-course-slug)"

# Using just the slug
dl-ai my-course-slug

# With custom output directory and concurrency
dl-ai my-course-slug --output-dir ./my-courses --concurrent 3
```

### Download a Specialization Bundle

You can download all sub-courses within a Specialization track automatically using `-s` or `--specialization`:

```bash
# Download a full specialization by slug
dl-ai -s generative-ai-for-software-development

# Download with custom output directory and concurrency
dl-ai -s generative-ai-for-software-development -o ./specializations -c 2 -b chrome
```

### Download Enrolled Courses

```bash
# Download studying courses only
dl-ai --enrolled studying

# Download finished courses only
dl-ai --enrolled finished

# Download all enrolled courses
dl-ai --enrolled all -o ./downloads -c 2 -b firefox
```

## Command Line Options

- `course` (positional, optional): Course URL or slug. Required if `--enrolled` or `--specialization` is not used.
- `-s, --specialization`: Specialization URL or slug. Downloads all sub-courses contained in the track.
- `-e, --enrolled`: Download enrolled courses. Choices: `studying`, `finished`, `all`.
- `-o, --output-dir`: Directory where courses will be saved (default: `./courses`).
- `-c, --concurrent`: Number of lessons to download concurrently per course (default: `1`).
- `-b, --browser`: Browser to extract cookies from (default: `chrome`). Supported: `chrome`, `chromium`, `opera`, `opera_gx`, `brave`, `edge`, `vivaldi`, `firefox`, `librewolf`, `safari`.

## Features

- ✅ Download individual courses, entire specializations, or enrolled courses
- ✅ Download videos, captions (`.vtt`), and reading materials (`.md`)
- ✅ Concurrent lesson downloads with stable progress bars
- ✅ Automatic tRPC schema fallback and payload normalisation
- ✅ Error handling and recovery

## Requirements

- Python 3.8+
- requests
- yt-dlp
- tqdm
- pydantic >= 2.0.0
- browser-cookie3

## License

MIT License
