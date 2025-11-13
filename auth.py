"""
Authentication module for DeepLearning.AI Course Downloader.

This module handles browser cookie extraction using browser_cookie3.
"""

import logging
from http.cookiejar import CookieJar

import requests

try:
    import browser_cookie3
except ImportError:
    browser_cookie3 = None


# Default headers to use for requests
DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,ar;q=0.8,fr;q=0.7,pt;q=0.6,ms;q=0.5",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
}

# Supported browsers
SUPPORTED_BROWSERS = [
    "chrome",
    "chromium",
    "opera",
    "opera_gx",
    "brave",
    "edge",
    "vivaldi",
    "firefox",
    "librewolf",
    "safari",
]


def get_cookies_from_browser(browser: str, domain_name: str = "deeplearning.ai") -> CookieJar:
    """
    Extract cookies from a browser for the specified domain.

    Args:
        browser: Browser name (chrome, chromium, opera, opera_gx, brave, edge,
                 vivaldi, firefox, librewolf, safari)
        domain_name: Domain name to extract cookies for (default: "deeplearning.ai")

    Returns:
        Dictionary of cookie name-value pairs

    Raises:
        ImportError: If browser_cookie3 is not installed
        RuntimeError: If browser is not supported or cookies cannot be extracted
    """
    if browser_cookie3 is None:
        raise ImportError("browser_cookie3 is required. Install it with: pip install browser-cookie3")

    if browser not in SUPPORTED_BROWSERS:
        raise RuntimeError(f"Unsupported browser: {browser}. Supported browsers: {', '.join(SUPPORTED_BROWSERS)}")

    try:
        # Map browser names to browser_cookie3 functions
        browser_map = {
            "chrome": browser_cookie3.chrome,
            "chromium": browser_cookie3.chromium,
            "opera": browser_cookie3.opera,
            "opera_gx": browser_cookie3.opera_gx,
            "brave": browser_cookie3.brave,
            "edge": browser_cookie3.edge,
            "vivaldi": browser_cookie3.vivaldi,
            "firefox": browser_cookie3.firefox,
            "librewolf": browser_cookie3.librewolf,
            "safari": browser_cookie3.safari,
        }

        # Get cookie jar from browser
        cookie_jar = browser_map[browser](domain_name=domain_name)

        if not cookie_jar or len(cookie_jar) == 0:
            raise RuntimeError(
                f"No cookies found for domain '{domain_name}' in {browser}. "
                "Make sure you are logged into DeepLearning.AI in your browser."
            )

        logging.debug(f"Extracted {len(cookie_jar)} cookies from {browser} for {domain_name}")
        return cookie_jar

    except Exception as e:
        raise RuntimeError(
            f"Failed to extract cookies from {browser}: {e}. "
            "Make sure the browser is installed and you are logged into DeepLearning.AI."
        ) from e


def create_session(browser: str = "chrome") -> requests.Session:
    """
    Create a requests session with cookies and headers configured.

    Args:
        browser: Browser name to extract cookies from (default: "chrome")

    Returns:
        Configured requests.Session instance
    """
    session = requests.Session()

    # Get cookies and headers
    cookie_jar = get_cookies_from_browser(browser)

    # Assign CookieJar directly to session
    session.cookies = cookie_jar  # type: ignore

    # Set default headers
    session.headers.update(DEFAULT_HEADERS)

    return session
