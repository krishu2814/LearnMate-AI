from app.models.course import DifficultyLevel


def build_remediation_quiz_prompt(
    weak_topics: list[str],
    missed_questions: list[dict],
    num_questions: int,
    difficulty: DifficultyLevel,
) -> str:
    """Build prompt for AI remediation quiz targeting the student's specific misconceptions."""
    topics_str = ", ".join(weak_topics) if weak_topics else "Core Concepts"

    missed_summary = []
    for mq in missed_questions[:5]:
        missed_summary.append(
            f"- Concept/Tag: {mq.get('topic_tag', 'General')}\n"
            f"  Question: {mq.get('question')}\n"
            f"  Expected Understanding: {mq.get('correct_answer')}\n"
            f"  Why it matters: {mq.get('explanation', '')}"
        )
    missed_text = "\n".join(missed_summary) if missed_summary else "General weakness remediation."

    prompt = (
        f"You are LearnMate AI's Adaptive Assessment and Remediation Specialist.\n"
        f"A student has struggled with specific concepts and needs a targeted remediation quiz "
        f"to fix their misunderstandings and solidify conceptual mastery.\n\n"
        f"--- Learner Weakness Profile ---\n"
        f"Identified Weak Topics: {topics_str}\n"
        f"Target Difficulty Level: {difficulty.value.upper()}\n"
        f"Requested Questions Count: {num_questions}\n\n"
        f"--- Specific Questions Previously Missed ---\n"
        f"{missed_text}\n"
        f"-------------------------------------------\n\n"
        f"Pedagogical Objective:\n"
        f"1. Generate {num_questions} fresh, original assessment questions specifically targeting "
        f"the misconceptions indicated above.\n"
        f"2. Do NOT simply copy the previous questions verbatim; craft novel problem scenarios, "
        f"edge cases, or varied framing to test true understanding.\n"
        f"3. For every question, provide 4 plausible options for Multiple Choice (mcq) or 2 for True/False (true_false).\n"
        f"4. Provide exceptionally clear and encouraging 'explanation' strings breaking down the underlying principle.\n"
    )
    return prompt

