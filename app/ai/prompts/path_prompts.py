from app.models.course import DifficultyLevel


def build_curriculum_prompt(
    goal: str,
    difficulty: DifficultyLevel,
    total_days: int,
    daily_minutes: int,
    catalog_summary: list[dict],
    custom_focus: str | None = None,
) -> str:
    """Build system-engineered prompt for generating an AI personalized curriculum."""
    catalog_lines = []
    for item in catalog_summary:
        catalog_lines.append(
            f"- Course: '{item['course_title']}' | Module: '{item['module_title']}' | "
            f"Lesson ID: '{item['lesson_id']}' | Title: '{item['lesson_title']}' | "
            f"Est: {item['estimated_minutes']}m"
        )
    catalog_text = "\n".join(catalog_lines) if catalog_lines else "No specific catalog provided."

    prompt = (
        f"You are LearnMate AI, an elite educational architect and personalized curriculum planner.\n"
        f"Create an optimal, highly structured study path tailored to the student's background and constraints.\n\n"
        f"--- Learner Profile & Constraints ---\n"
        f"- Target Goal: {goal}\n"
        f"- Current Level: {difficulty.value.upper()}\n"
        f"- Timeline Budget: {total_days} total days @ {daily_minutes} minutes/day "
        f"(Total study budget: {total_days * daily_minutes} minutes)\n"
    )

    if custom_focus:
        prompt += f"- Custom Topic Focus: {custom_focus}\n"

    prompt += (
        f"\n--- Available Catalog of Lessons ---\n"
        f"{catalog_text}\n"
        f"------------------------------------\n\n"
        f"Requirements:\n"
        f"1. Select the most relevant lessons from the catalog above to achieve the learner's goal.\n"
        f"2. Return the exact lesson IDs in 'selected_lesson_ids' in the pedagogical sequence they should be studied.\n"
        f"3. Divide the curriculum into sequential 'weekly_milestones' (e.g. 'Week 1: Core Fundamentals & Setup', 'Week 2: ...').\n"
        f"4. Provide a strategic 'overview' explaining how this path takes the student from their current level to mastery.\n"
        f"5. Include 3-5 concrete 'study_tips' (e.g., active recall strategies, code repetition, project application).\n"
    )
    return prompt
