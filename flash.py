from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

from fastapi.responses import RedirectResponse


def redirect_with_flash(url: str, message: str, level: str = "success") -> RedirectResponse:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    query["flash"] = message
    query["level"] = level
    new_query = urlencode(query)
    final_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    return RedirectResponse(url=final_url, status_code=303)

