# Banana API

This skill targets the Banana/Jiekou image endpoint:

`https://api.jiekou.ai/v3/gemini-3-pro-image-text-to-image`

## Authentication

Pass the bearer token through an environment variable.

Supported names:

- `BANANA_API_KEY`
- `API_KEY`

## Request Shape

```json
{
  "size": "1K",
  "google": {
    "web_search": false
  },
  "prompt": "Create a clean paper-style method illustration ...",
  "aspect_ratio": "16:9",
  "output_format": "image/png"
}
```

## Notes

- `web_search` should normally remain `false` for illustration generation.
- `output_format` defaults well to `image/png`.
- Prefer explicit aspect ratios such as `16:9`, `4:3`, or `1:1`.
- The endpoint may return raw image bytes or a JSON payload. The script handles both common cases.
