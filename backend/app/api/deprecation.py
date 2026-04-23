from fastapi import Response


def add_deprecation_header(response: Response, alternative: str) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-07-01"
    response.headers["Link"] = f'<{alternative}>; rel="successor-version"'
