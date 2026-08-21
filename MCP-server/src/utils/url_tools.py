def improve_url(url: str, page: str | None) -> str:
    if not url:
        return ""

    if url.endswith("?forcedownload=1"):
        url = url[: -len("?forcedownload=1")]

    if page:
        url += f"#page={page}"

    return url
