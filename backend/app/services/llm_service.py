from typing import List, Dict, Any
import logging

from ..config import settings
from .retriever import RetrievedSource

logger = logging.getLogger(__name__)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are a document question-answering assistant.

Your job is to answer the user's question using ONLY the
retrieved context from the uploaded document.

============================================================
ANSWER STYLE
============================================================

1. Give the direct answer first.

2. Then explain the answer in simple and clear language.

3. Give enough detail for the user to properly understand
   the answer, but do NOT make the answer unnecessarily long.

4. Do not simply copy large portions of the document.

5. Do not give a one-line answer unless the question only
   requires a one-line answer.

6. For normal questions, aim for around 3-7 sentences.

7. For questions asking to explain a concept, give:
   - Definition / direct answer
   - Simple explanation
   - Important points
   - Example or working only if it is present or supported
     by the document

8. For algorithm questions:
   - State what the algorithm does
   - Explain the main steps
   - Mention important details from the document
   - Mention complexity if the document provides it

9. For complexity questions:
   - State the complexity clearly
   - Explain why in simple language
   - Show the important derivation only when useful

10. Use bullet points when they make the answer easier to read.

11. Use simple language. Avoid unnecessarily complicated
    technical words.

12. Do not repeat the user's question.

============================================================
DOCUMENT GROUNDING
============================================================

13. Use ONLY the retrieved context provided to you.

14. Do NOT use outside knowledge.

15. Do NOT make assumptions.

16. Do NOT invent information.

17. Do NOT hallucinate.

18. If the answer cannot be found in the retrieved context,
    respond exactly:

"I could not find this information in the uploaded document."

19. Do not answer a question using general knowledge just
    because you know the answer.

============================================================
SOURCE
============================================================

20. When a relevant page number is available, mention it
    naturally at the end of the answer using:

[Page X]

============================================================
GOAL
============================================================

The ideal response should be:

DIRECT + SIMPLE + CLEAR + DETAILED ENOUGH TO UNDERSTAND

Do not be too short.
Do not be unnecessarily long.
"""


class LLMService:
    """
    LLM service supporting Google Gemini and OpenAI.

    The LLM receives only the retrieved document context.
    This helps keep answers grounded in the uploaded documents.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.gemini_key = settings.GEMINI_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

        self.openai_client = None

        self._init_providers()

    # ============================================================
    # INITIALIZE PROVIDERS
    # ============================================================

    def _init_providers(self):
        """Configure available LLM providers."""

        # --------------------------------------------------------
        # Gemini
        # --------------------------------------------------------

        if self.gemini_key:
            try:
                import google.generativeai as genai

                genai.configure(
                    api_key=self.gemini_key
                )

                logger.info(
                    f"Gemini API configured with model "
                    f"'{settings.GEMINI_MODEL}'"
                )

            except Exception as e:
                logger.warning(
                    f"Failed to configure Gemini: {e}"
                )

        # --------------------------------------------------------
        # OpenAI
        # --------------------------------------------------------

        if self.openai_key:
            try:
                import openai

                self.openai_client = openai.OpenAI(
                    api_key=self.openai_key
                )

                logger.info(
                    f"OpenAI API configured with model "
                    f"'{settings.OPENAI_MODEL}'"
                )

            except Exception as e:
                self.openai_client = None

                logger.warning(
                    f"Failed to configure OpenAI: {e}"
                )

    # ============================================================
    # PROVIDER STATUS
    # ============================================================

    def get_status(self) -> Dict[str, Any]:
        """
        Return provider information without exposing API keys.
        """

        active_provider = "none"

        if (
            self.provider == "gemini"
            and self.gemini_key
        ):
            active_provider = (
                f"gemini ({settings.GEMINI_MODEL})"
            )

        elif (
            self.provider == "openai"
            and self.openai_key
        ):
            active_provider = (
                f"openai ({settings.OPENAI_MODEL})"
            )

        elif self.gemini_key:
            active_provider = (
                f"gemini ({settings.GEMINI_MODEL})"
            )

        elif self.openai_key:
            active_provider = (
                f"openai ({settings.OPENAI_MODEL})"
            )

        return {
            "active_provider": active_provider,
            "has_gemini_key": bool(self.gemini_key),
            "has_openai_key": bool(self.openai_key),
            "gemini_model": settings.GEMINI_MODEL,
            "openai_model": settings.OPENAI_MODEL,
        }

    # ============================================================
    # GENERATE ANSWER
    # ============================================================

    def generate_answer(
        self,
        question: str,
        retrieved_sources: List[RetrievedSource],
        context_text: str
    ) -> str:
        """
        Generate a document-grounded answer.

        The answer is generated only from retrieved context.
        """

        # --------------------------------------------------------
        # No retrieval result
        # --------------------------------------------------------

        if (
            not retrieved_sources
            or not context_text.strip()
        ):
            return (
                "I could not find this information "
                "in the uploaded document."
            )

        # --------------------------------------------------------
        # Build user prompt
        # --------------------------------------------------------

        user_prompt = f"""
RETRIEVED CONTEXT FROM THE UPLOADED DOCUMENT
============================================================

{context_text}


USER QUESTION
============================================================

{question}


ANSWER INSTRUCTIONS
============================================================

Answer the user's question using ONLY the retrieved context.

Follow this structure when appropriate:

1. Direct Answer
   Give the answer immediately.

2. Explanation
   Explain the answer in simple language.

3. Important Details
   Include the important supporting information from
   the document.

Keep the response detailed enough to understand,
but do not make it unnecessarily long.

For a simple factual question:
- Give the direct answer.
- Add a short explanation.

For a conceptual question:
- Give the definition.
- Explain it simply.
- Add important points.

For an algorithm question:
- Explain what it does.
- Explain the main steps.
- Mention complexity if available.

For a complexity question:
- State the complexity.
- Explain the reason simply.
- Include the derivation only if useful.

IMPORTANT:

Do not use information outside the retrieved context.

Do not make assumptions.

Do not invent information.

Do not repeat the question.

If the answer is not present in the retrieved context,
respond exactly:

I could not find this information in the uploaded document.

If a page number is available, mention it at the end as:

[Page X]
"""

        # ========================================================
        # GEMINI
        # ========================================================

        if (
            self.provider == "gemini"
            and self.gemini_key
        ):
            try:
                return self._call_gemini(
                    user_prompt
                )

            except Exception as e:

                logger.error(
                    f"Gemini API call failed: {e}"
                )

                # ------------------------------------------------
                # OpenAI fallback
                # ------------------------------------------------

                if self.openai_key:

                    logger.info(
                        "Falling back to OpenAI..."
                    )

                    try:
                        return self._call_openai(
                            user_prompt
                        )

                    except Exception as oe:

                        logger.error(
                            f"OpenAI fallback also failed: {oe}"
                        )

                return (
                    "There was an error while generating "
                    "the answer using Gemini. "
                    "Please check your GEMINI_API_KEY "
                    "in the .env file."
                )

        # ========================================================
        # OPENAI
        # ========================================================

        if self.openai_key:

            try:
                return self._call_openai(
                    user_prompt
                )

            except Exception as e:

                logger.error(
                    f"OpenAI API call failed: {e}"
                )

                return (
                    "There was an error while generating "
                    "the answer using OpenAI. "
                    "Please check your OPENAI_API_KEY "
                    "in the .env file."
                )

        # ========================================================
        # NO API KEY
        # ========================================================

        return self._generate_keyless_summary(
            question,
            retrieved_sources
        )

    # ============================================================
    # GEMINI
    # ============================================================

    def _call_gemini(
        self,
        user_prompt: str
    ) -> str:
        """Send the prompt to Gemini."""

        import google.generativeai as genai

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT
        )

        response = model.generate_content(
            user_prompt,

            generation_config=genai.types.GenerationConfig(
                # Low temperature keeps answers factual
                temperature=0.1,

                # Enough room for detailed but concise answers
                max_output_tokens=700,
            )
        )

        if not response.text:
            return (
                "I could not generate an answer "
                "from the uploaded document."
            )

        return response.text.strip()

    # ============================================================
    # OPENAI
    # ============================================================

    def _call_openai(
        self,
        user_prompt: str
    ) -> str:
        """Send the prompt to OpenAI."""

        if not self.openai_client:
            raise RuntimeError(
                "OpenAI client is not configured."
            )

        response = (
            self.openai_client
            .chat.completions.create(

                model=settings.OPENAI_MODEL,

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],

                temperature=0.1,

                max_tokens=700
            )
        )

        answer = (
            response
            .choices[0]
            .message
            .content
        )

        if not answer:
            return (
                "I could not generate an answer "
                "from the uploaded document."
            )

        return answer.strip()

    # ============================================================
    # KEYLESS FALLBACK
    # ============================================================

    def _generate_keyless_summary(
        self,
        question: str,
        sources: List[RetrievedSource]
    ) -> str:
        """
        Fallback when no LLM API key is configured.

        This does not generate an answer.
        It displays the most relevant retrieved passage.
        """

        if not sources:
            return (
                "I could not find this information "
                "in the uploaded document."
            )

        top_source = sources[0]

        # --------------------------------------------------------
        # Page / section
        # --------------------------------------------------------

        if top_source.page:
            page_str = f"Page {top_source.page}"
        else:
            page_str = (
                f"Section: {top_source.section}"
            )

        # --------------------------------------------------------
        # Excerpt
        # --------------------------------------------------------

        excerpt = top_source.text.strip()

        if len(excerpt) > 500:
            excerpt = excerpt[:500] + "..."

        return (
            "**Local Retrieval Mode**\n\n"

            f"Relevant information was retrieved from "
            f"**{top_source.document_name}** "
            f"({page_str}).\n\n"

            "**Relevant Excerpt:**\n"

            f"> {excerpt}\n\n"

            "To enable AI-generated answers, configure "
            "`GEMINI_API_KEY` in `.env`."
        )


# ================================================================
# SINGLETON
# ================================================================

_llm_service_instance = None


def get_llm_service() -> LLMService:
    """
    Return a shared LLM service instance.
    """

    global _llm_service_instance

    if _llm_service_instance is None:
        _llm_service_instance = LLMService()

    return _llm_service_instance