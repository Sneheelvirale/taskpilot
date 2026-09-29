import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from app.schemas import TaskExtractionResult

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

def extract_tasks_with_nemotron(document_text: str) -> TaskExtractionResult:
    api_key = os.getenv("NEBIUS_API_KEY")
    model = os.getenv("NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning")

    if not api_key:
        raise RuntimeError("NEBIUS_API_KEY is not set in backend/.env file")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.tokenfactory.nebius.com/v1/",
    )

    system_prompt = """
You are TaskPilot, an AI document analyzer.
Your task is to analyze the user document and output ONLY valid JSON matching this exact structure:

{
  "document_summary": "High-level summary of the document contents.",
  "tasks": [
    {
      "title": "Short title of the task",
      "deadline": "YYYY-MM-DD or Unknown",
      "priority": "High",
      "action_required": "Detailed action step required"
    }
  ]
}

CRITICAL RULES:
1. Do NOT include markdown formatting like ```json or ```.
2. Priority MUST be one of: "High", "Medium", or "Low".
3. Return raw JSON ONLY. No conversational text before or after.
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document Text:\n{document_text[:8000]}"},
        ],
        temperature=0.1
    )

    raw_content = response.choices[0].message.content.strip()

    # Clean markdown quotes if model adds them
    if "```" in raw_content:
        raw_content = re.sub(r'```(?:json)?', '', raw_content).strip()

    try:
        parsed_data = json.loads(raw_content)
    except Exception:
        # Fallback parsing attempt if output contains unexpected formatting
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        if json_match:
            parsed_data = json.loads(json_match.group(0))
        else:
            parsed_data = {}

    # Safeguard missing fields to prevent Pydantic validation crashes
    if "document_summary" not in parsed_data or not isinstance(parsed_data["document_summary"], str):
        parsed_data["document_summary"] = "Extracted analysis from uploaded document."

    if "tasks" not in parsed_data or not isinstance(parsed_data["tasks"], list):
        parsed_data["tasks"] = [
            {
                "title": "Review Document Output",
                "deadline": "Unknown",
                "priority": "Medium",
                "action_required": "Check uploaded document for specific details."
            }
        ]

    return TaskExtractionResult(**parsed_data)