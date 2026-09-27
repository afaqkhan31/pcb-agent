"""Sprint 1 smoke test: proves your API key, SDK and model name all work.

Run:  python -m agents.hello_gemini
"""
from agents.llm import MODEL, client


def main() -> None:
    response = client.models.generate_content(
        model=MODEL,
        contents="In one sentence, why should a 5V power trace be wider than an I2C signal trace?",
    )
    print(f"[model: {MODEL}]")
    print(response.text)


if __name__ == "__main__":
    main()
