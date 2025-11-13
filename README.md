# DeepLearning.AI Course Downloader

A Python CLI tool to download courses from DeepLearning.AI, including videos, captions, and reading materials.

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd deeplearning_ai_courses_downloader

# Install in development mode
pip install -e .

# Or install normally
pip install .
```

### Direct Install (if published)

```bash
pip install dl-ai
```

## Configuration

The tool automatically extracts authentication cookies from your browser. **Make sure you are logged into DeepLearning.AI in your browser** before running the downloader.

The tool supports the following browsers:
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
dl-ai "https://learn.deeplearning.ai/courses/my-course-slug"

# Using just the slug
dl-ai my-course-slug

# With custom output directory
dl-ai my-course-slug --output-dir ./my-courses

# With concurrent downloads (faster)
dl-ai my-course-slug --concurrent 3

# Specify browser to extract cookies from (default: chrome)
dl-ai my-course-slug --browser firefox

# Combine options
dl-ai my-course-slug --browser chrome --output-dir ./my-courses --concurrent 3
```

### Download Enrolled Courses

```bash
# Download studying courses only
dl-ai --enrolled studying

# Download finished courses only
dl-ai --enrolled finished

# Download all enrolled courses
dl-ai --enrolled all

  # With options
  dl-ai --enrolled all -o ./downloads -c 2 -b firefox
```

## Command Line Options

- `course` (positional, optional): Course URL or slug. Required if `--enrolled` is not used.
- `-e, --enrolled`: Download enrolled courses. Choices: `studying`, `finished`, `all`
- `-o, --output-dir`: Directory where courses will be saved (default: `./courses`)
- `-c, --concurrent`: Number of lessons to download concurrently (default: `1`)
- `-b, --browser`: Browser to extract cookies from (default: `chrome`). Supported: `chrome`, `chromium`, `opera`, `opera_gx`, `brave`, `edge`, `vivaldi`, `firefox`, `librewolf`, `safari`

## Features

- ✅ Download videos, captions, and reading materials
- ✅ Concurrent downloads for faster processing
- ✅ Progress bars with tqdm
- ✅ Download enrolled courses (studying/finished/all)
- ✅ Automatic 1-minute delay between course downloads
- ✅ Error handling and recovery
- ✅ Course information saved as markdown

## Requirements

- Python 3.8+
- requests
- yt-dlp
- tqdm
- pydantic
- browser-cookie3

**Note**: Make sure you are logged into DeepLearning.AI in your browser before running the downloader. The tool extracts authentication cookies from your browser automatically.

## License

MIT License



