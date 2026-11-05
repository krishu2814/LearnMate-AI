from app.models.course import DifficultyLevel
from app.models.quiz import QuestionType


def build_quiz_generation_prompt(
    topic: str,
    difficulty: DifficultyLevel,
    num_questions: int,
    lesson_title: str | None = None,
    lesson_content: str | None = None,
    allowed_types: list[QuestionType] | None = None,
    custom_instructions: str | None = None,
) -> str:
    """Build system-engineered prompt for generating a structured quiz."""
    types_str = ", ".join(t.value for t in allowed_types) if allowed_types else "mcq, true_false"

    prompt = (
        f"You are LearnMate AI, a world-class educational curriculum engineer and adaptive assessment designer.\n"
        f"Generate a rigorous, high-quality assessment quiz adhering to the following parameters:\n"
        f"- Topic: {topic}\n"
        f"- Target Difficulty: {difficulty.value.upper()}\n"
        f"- Number of Questions: {num_questions}\n"
        f"- Allowed Question Types: {types_str}\n"
    )

    if lesson_title and lesson_content:
        prompt += (
            f"\n--- Grounded Lesson Context ---\n"
            f"Lesson Title: {lesson_title}\n"
            f"Lesson Content:\n{lesson_content}\n"
            f"--------------------------------\n"
            f"Instruction: Anchor the questions specifically in the concepts, nuances, and code taught in this lesson content.\n"
        )
    else:
        prompt += (
            f"\nInstruction: Base the questions on modern industry best practices and core foundational knowledge for {topic}.\n"
        )

    if custom_instructions:
        prompt += f"\nCustom Pedagogical Guidance: {custom_instructions}\n"

    prompt += (
        "\nRules for Question Construction:\n"
        "1. For Multiple Choice Questions (mcq):\n"
        "   - Provide exactly 4 distinct, plausible options.\n"
        "   - Ensure exactly ONE option is completely correct.\n"
        "   - The 'correct_answer' field MUST exactly match one of the entries in 'options'.\n"
        "2. For True/False Questions (true_false):\n"
        "   - 'options' must be ['True', 'False'].\n"
        "   - 'correct_answer' must be either 'True' or 'False'.\n"
        "3. Every question must include a lucid, pedagogical 'explanation' outlining why the answer is correct and why common misconceptions fail.\n"
        "4. Assign an appropriate 'topic_tag' representing the specific subtopic or concept tested.\n"
    )

    return prompt


def build_answer_evaluation_prompt(
    question_text: str,
    question_type: str,
    correct_answer: str,
    user_answer: str,
    explanation: str | None = None,
) -> str:
    """Build prompt for semantic evaluation and adaptive feedback on a student's answer."""
    return (
        f"You are an expert tutor assessing a student's response on LearnMate AI.\n\n"
        f"Question: {question_text}\n"
        f"Question Type: {question_type}\n"
        f"Standard Correct Answer: {correct_answer}\n"
        f"Reference Explanation: {explanation or 'N/A'}\n"
        f"Student's Submitted Answer: {user_answer}\n\n"
        f"Task:\n"
        f"1. Evaluate whether the student's answer demonstrates accurate conceptual understanding.\n"
        f"   - For MCQ/True-False: verify if the answer matches the correct choice or expresses the exact same concept.\n"
        f"   - Be fair: tolerate minor typos, casing differences, or equivalent synonyms if the meaning is unequivocally correct.\n"
        f"2. Provide a confidence score between 0.0 (completely uncertain) and 1.0 (absolutely certain).\n"
        f"3. Provide brief, encouraging, and actionable educational feedback (1-3 sentences) explaining why their answer is right or where their reasoning fell short.\n"
    )
