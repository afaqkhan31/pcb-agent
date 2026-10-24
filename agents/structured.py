"""One shared helper: ask Gemini for JSON that matches a Pydantic schema.

Retries when the free tier is busy (429/500/503). Every agent can use it.
"""
from __future__ import annotations

import time
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
RETRY_CODES = (429, 500, 503)


def ask_structured(contents: str, system: str, schema: type[T], temperature: float = 0.1,
                   tries: int = 3) -> T:
    # Imported here so modules that only *might* call Gemini load without an API key.
    from google.genai import errors, types

    from agents.llm import MODEL, client

    for attempt in range(1, tries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=temperature,
                ),
            )
            break
        except errors.APIError as e:
            if e.code in RETRY_CODES and attempt < tries:
                print(f"  (Gemini busy: {e.code}. Retrying in {5 * attempt} s...)")
                time.sleep(5 * attempt)
            else:
                raise
    parsed = response.parsed
    return parsed if parsed is not None else schema.model_validate_json(response.text)
