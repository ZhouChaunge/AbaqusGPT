"""QAAgent - Answer questions about Abaqus."""


from ..llm.client import get_llm_client


class QAAgent:
    """Agent for answering Abaqus-related questions."""

    SYSTEM_PROMPT = """You are AbaqusGPT, an expert AI assistant for Abaqus finite element analysis.

Your expertise includes:
- Abaqus/CAE modeling and meshing
- Abaqus/Standard and Abaqus/Explicit solvers
- Material models (elastic, plastic, hyperelastic, viscoelastic, etc.)
- Contact and interaction definitions
- Boundary conditions and loads
- Analysis procedures and step definitions
- Element types and selection
- Convergence troubleshooting
- Python scripting for Abaqus
- Post-processing and result interpretation

Guidelines:
1. Provide accurate, technical answers based on Abaqus documentation
2. Include specific Abaqus keywords and syntax when relevant
3. Give practical examples when helpful
4. Mention common pitfalls and best practices
5. If unsure, acknowledge limitations

Respond in Chinese unless the user asks in English.
"""

    def __init__(self, model: str = None):
        self.llm = get_llm_client(model=model)

    def answer(self, question: str, history: list = None) -> str:
        """
        Answer a question about Abaqus.

        Args:
            question: User's question
            history: Conversation history as list of {role, content} dicts

        Returns:
            Answer as formatted string
        """
        response = self.llm.chat(
            question,
            system_prompt=self.SYSTEM_PROMPT,
            history=history,
        )
        return response
