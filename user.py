import json

import requests


class User:
    def __init__(self, session: requests.Session):
        """
        Initialize User with a requests session.

        Args:
            session: Configured requests.Session instance with cookies and headers
        """
        self.session = session
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

        response = self.session.get(self.TRPC_ENDPOINT, params=params)

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
