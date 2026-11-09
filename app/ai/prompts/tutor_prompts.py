def build_lesson_explanation_prompt(
    lesson_title: str,
    lesson_content: str,
    style: str,
    focus_question: str | None = None,
) -> str:
    """Build prompt for multi-style pedagogical lesson explanations."""
    style_guidelines = {
        "beginner": "Explain using intuitive, approachable language with everyday real-world metaphors (ELI5 style). Avoid dense jargon without explaining it.",
        "deep_dive": "Provide an architectural deep dive exploring underlying mechanics, memory/runtime implications, edge cases, and internals.",
        "analogy": "Frame the entire core concept around a vivid, relatable real-world analogy to make abstract concepts click immediately.",
        "practical": "Emphasize production patterns, hands-on implementation tips, anti-patterns to avoid, and industry real-world use cases.",
    }
    guideline = style_guidelines.get(style, style_guidelines["deep_dive"])

    prompt = (
        f"You are LearnMate AI's master tutor.\n"
        f"Your task is to teach the concepts in the lesson below to a student seeking clarification.\n\n"
        f"--- Lesson Information ---\n"
        f"Lesson Title: {lesson_title}\n"
        f"Lesson Content:\n{lesson_content}\n"
        f"--------------------------\n\n"
        f"Explanation Style Requested: {style.upper()}\n"
        f"Style Directive: {guideline}\n"
    )

    if focus_question:
        prompt += f"\nSpecific Student Question: '{focus_question}'\n"

    prompt += (
        "\nOutput Requirements:\n"
        "1. 'explanation': A comprehensive, engaging explanation adhering to the requested style.\n"
        "2. 'key_takeaways': 3 to 5 actionable bullet points summarizing the core mental models.\n"
        "3. 'code_example': A clean, commented code snippet illustrating the concept (or null if purely theoretical).\n"
        "4. 'suggested_followups': 2 to 3 insightful follow-up questions to test or deepen understanding.\n"
    )
    return prompt


def build_socratic_tutor_prompt(
    message: str,
    lesson_title: str | None = None,
    lesson_content: str | None = None,
    history: list[dict] | None = None,
) -> str:
    """Build prompt for conversational Socratic tutoring."""
    prompt = (
        "You are LearnMate AI's Socratic Tutor, an encouraging, deeply knowledgeable engineering mentor.\n"
        "Principles of Socratic Mentorship:\n"
        "1. Guide the student towards discovering solutions themselves rather than just giving the direct answer immediately.\n"
        "2. Break down complex questions into simpler conceptual building blocks.\n"
        "3. Always check for understanding with a thoughtful 'socratic_question'.\n"
        "4. Keep explanations concise, clear, and technically accurate.\n"
    )

    if lesson_title and lesson_content:
        prompt += (
            f"\n--- Current Lesson Context ---\n"
            f"Lesson: {lesson_title}\n"
            f"Content Summary: {lesson_content[:1500]}\n"
            f"------------------------------\n"
        )

    if history:
        prompt += "\n--- Conversation History ---\n"
        for msg in history[-6:]:
            role = "Student" if msg.get("role") == "user" else "Tutor"
            prompt += f"{role}: {msg.get('content')}\n"
        prompt += "----------------------------\n"

    prompt += (
        f"\nStudent's Latest Message: {message}\n\n"
        "Task:\n"
        "1. 'reply': A warm, pedagogical response addressing the student's thought process.\n"
        "2. 'socratic_question': A single focused, guiding question to prompt the student to take the next cognitive step.\n"
        "3. 'suggested_topics': 2-3 related topics the student might explore next.\n"
    )
    return prompt

