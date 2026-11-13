from app.models.course import DifficultyLevel


def build_code_review_prompt(
    title: str,
    language: str,
    source_code: str,
    problem_description: str | None = None,
    lesson_title: str | None = None,
    lesson_content: str | None = None,
) -> str:
    """Build system-engineered prompt for comprehensive AI code review and complexity analysis."""
    prompt = (
        f"You are LearnMate AI's Senior Principal Software Engineer and Code Reviewer.\n"
        f"Perform an exhaustive, rigorous, and pedagogical review of the student's submitted code.\n\n"
        f"--- Submission Details ---\n"
        f"Title: {title}\n"
        f"Language: {language}\n"
    )

    if problem_description:
        prompt += f"Problem Specification / Goal: {problem_description}\n"

    if lesson_title and lesson_content:
        prompt += (
            f"\n--- Grounded Lesson Context ---\n"
            f"Lesson Title: {lesson_title}\n"
            f"Lesson Content Summary: {lesson_content[:1500]}\n"
            f"--------------------------------\n"
        )

    prompt += (
        f"\n--- Student Source Code ---\n"
        f"```{language}\n"
        f"{source_code}\n"
        f"```\n"
        f"---------------------------\n\n"
        "Evaluation Directives:\n"
        "1. Correctness & Runtime Safety: Identify syntax errors, logic bugs, unhandled exceptions, race conditions, blocking calls in async loops, or memory leaks.\n"
        "2. Algorithmic Complexity: Determine exact Time Complexity (e.g. 'O(n)', 'O(n log n)', 'O(1)') and Space Complexity (e.g. 'O(1)', 'O(n)').\n"
        "3. Idiomatic Style & Clean Architecture: Check PEP 8 / language best practices, modularity, type hints, naming conventions.\n"
        "4. Constructive Feedback:\n"
        "   - 'score': An integer score from 0 to 100 based on correctness, quality, and efficiency.\n"
        "   - 'is_passed': True if score >= 70 and has no critical bugs, otherwise False.\n"
        "   - 'review_summary': A clear paragraph outlining the overall assessment and mental model recommendations.\n"
        "   - 'strengths': 2 to 4 bullet points highlighting what the student did well.\n"
        "   - 'issues': Structured list of issues. Each with 'line_number' (or null), 'severity' ('info', 'warning', 'critical'), 'message', and 'suggestion'.\n"
        "   - 'refactored_code': A complete, elegant, production-grade refactored rewrite demonstrating optimal architecture with helpful comments.\n"
    )
    return prompt


def build_exercise_generation_prompt(
    topic: str,
    difficulty: DifficultyLevel,
    lesson_title: str | None = None,
    lesson_content: str | None = None,
    custom_instructions: str | None = None,
) -> str:
    """Build prompt for generating practical hands-on coding exercises."""
    prompt = (
        f"You are LearnMate AI's Curriculum Engineering Specialist.\n"
        f"Design an engaging, practical hands-on coding challenge adhering to:\n"
        f"- Target Topic: {topic}\n"
        f"- Difficulty: {difficulty.value.upper()}\n"
    )

    if lesson_title and lesson_content:
        prompt += (
            f"\n--- Grounded Lesson Context ---\n"
            f"Lesson Title: {lesson_title}\n"
            f"Lesson Content Summary: {lesson_content[:1200]}\n"
        )

    if custom_instructions:
        prompt += f"\nCustom Pedagogical Guidance: {custom_instructions}\n"

    prompt += (
        "\nRequirements for the Coding Challenge:\n"
        "1. 'title': Engaging challenge title (e.g., 'Async Connection Queue with Timeout Backoff').\n"
        "2. 'description': Clear problem statement with constraints, input/output requirements, and edge cases.\n"
        "3. 'difficulty': Assessed difficulty level.\n"
        "4. 'starter_code': Clean starter boilerplate code with typing and docstrings for the student to complete.\n"
        "5. 'solution_code': Reference production-grade solution.\n"
        "6. 'test_cases': 3 to 5 test cases. Each with 'name', 'input_description', 'expected_output', and 'is_hidden' (boolean).\n"
        "7. 'hints': 2 to 3 progressive hints that guide without spoiling the solution.\n"
    )
    return prompt
