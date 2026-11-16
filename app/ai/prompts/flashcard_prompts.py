from app.models.course import DifficultyLevel


def build_flashcard_generation_prompt(
    topic: str,
    num_cards: int = 5,
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
    lesson_title: str | None = None,
    lesson_content: str | None = None,
    custom_instructions: str | None = None,
) -> str:
    """Construct prompt for synthesizing high-yield active recall flashcards with Gemini."""
    prompt = (
        "You are an expert cognitive scientist and educational technologist specializing in "
        "active recall and spaced repetition flashcard design.\n\n"
        f"Goal: Generate a concise, high-yield active recall flashcard deck on '{topic}'.\n"
        f"- Target Card Count: {num_cards}\n"
        f"- Difficulty Level: {difficulty.value.upper()}\n"
    )

    if lesson_title and lesson_content:
        prompt += (
            f"\n--- Grounded Lesson Context ---\n"
            f"Lesson Title: {lesson_title}\n"
            f"Lesson Content Excerpt:\n{lesson_content}\n"
            f"-------------------------------\n"
            "Instructions: Anchor the flashcard questions and answers directly to the facts, "
            "mental models, definitions, and code patterns taught in this lesson.\n"
        )
    else:
        prompt += (
            f"\nInstruction: Formulate cards covering core foundational principles, "
            f"common gotchas, and architectural trade-offs for {topic}.\n"
        )

    if custom_instructions:
        prompt += f"\nCustom Pedagogical Guidance: {custom_instructions}\n"

    prompt += (
        "\nCard Formulation Principles:\n"
        "1. Atomic Knowledge Principle: Each card must test exactly one atomic fact, definition, or concept.\n"
        "2. Clear Inversion / Question: The 'front' should be an unambiguous prompt or question requiring active recall.\n"
        "3. Precise & Digestible Answer: The 'back' must be concise (1-3 sentences or clean code snippet).\n"
        "4. Helpful Hints: Provide a subtle clue in 'hint' that jogs memory without revealing the core answer.\n"
        "5. Key Concept Tag: A short 2-4 word categorical tag in 'key_concept'.\n"
        "6. Output Format: Return a strictly validated JSON object conforming to AIGeneratedDeckPayload schema.\n"
    )

    return prompt
