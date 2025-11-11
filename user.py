import json

import requests

from utils import load_secret


class User:
    def __init__(self):
        self.cookies, self.headers = load_secret()
        self.BASE = "https://learn.deeplearning.ai"
        self.TRPC_ENDPOINT = f"{self.BASE}/api/trpc/course.enrolledCurriculumsV2"

    def _list_enrolled_courses(self, filter: str = "studying") -> list[dict]:
        """
        List the user's enrolled courses.

        Args:
            filter (str): Either "studying" or "finished". Determines which courses to list.
                          Defaults to "studying".

        Returns:
            list: List of enrolled courses data.

        Raises:
            ValueError: If filter is not "studying" or "finished".
            Exception: If the API request fails.
        """
        if filter not in ("studying", "finished"):
            raise ValueError("filter must be either 'studying' or 'finished'")

        # tRPC queries expect ?input=<JSON stringified object>
        params = {
            "batch": "1",
            "input": json.dumps({"0": {"json": {"filter": filter}}}),
        }

        response = requests.get(self.TRPC_ENDPOINT, params=params, headers=self.headers, cookies=self.cookies)

        if not response.ok:
            raise Exception(f"Failed to list studying courses: {response.status_code}")

        data = response.json()[0]["result"]["data"]["json"]["courses"]
        return data

    def list_studying_courses(self) -> list[dict]:
        return self._list_enrolled_courses(filter="studying")

    def list_finished_courses(self) -> list[dict]:
        return self._list_enrolled_courses(filter="finished")

    def list_all_courses(self) -> list[dict]:
        return self._list_enrolled_courses(filter="studying") + self._list_enrolled_courses(filter="finished")
