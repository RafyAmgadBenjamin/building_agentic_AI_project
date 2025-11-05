from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field


WEB_SEARCH_SUMMARIZER_PROMPT = PromptTemplate.from_template(
    """
    You are a helpful assistant that summarizes web search results to
    answer the user query.

    User query: {query}
    Search results: {search_results}

    Provide the answer in the following format:
    Answer: <answer>
    References:
    - <reference1>
    - <reference2>
    - ...

    where each reference is a url from the search results.
    """
)


# Used when we might/might not have answers in the document.
DOCUMENT_RAG_MIXED_PROMPT = PromptTemplate.from_template(
    """
    You are an assistant for question-answering tasks on Office of Personnel Management (OPM)
    annual performance documents for the years 2019, 2020, 2021, and 2022. Anything outside of
    this scope is not answerable from the documents.
    
    Use the provided pieces of retrieved context to answer the given question.
    Your response should be concise, consisting of three sentences maximum.
    If the answer is unknown, state explicitly that you do not know.


    Question: {question}
    Context: {retrieved_docs}

    # Steps

    1. Analyze the given question to understand what information is being sought.
    2. Review the provided context from retrieved documents to find relevant information.
    3. Formulate a concise answer in no more than three sentences.
    4. If the information cannot be found in the context, respond by stating that the answer is unknown.
    5. Optionally, list relevant sources provided.

    # Output Format

    - Answer: [Your concise answer in no more than three sentences]
    - Sources:
      - [Name of the document 1]
      - [Name of the document 2]

    # Examples

    Example 1:
    - **Question:** What are the effects of caffeine on sleep? 
    - **Context:** [Text from a research document explaining how caffeine delays sleep onset and reduces sleep quality.]
    - **Answer:** Caffeine can delay the onset of sleep and reduce overall sleep quality by affecting REM sleep cycles. 

    Example 2:
    - **Question:** Who currently holds the record for the fastest marathon time? 
    - **Context:** [Document discussing various marathon records but not mentioning current record-holder.]
    - **Answer:** I don't know.

    # Notes

    Ensure that the answer is supported by the context provided. Only use the context to generate your response to ensure accuracy.
    """
)

# Answer exists within the retrieved documents, just generate the answer.
DOCUMENT_RAG_PROMPT = PromptTemplate.from_template(
    """
    You are an assistant for question-answering tasks on Office of Personnel Management (OPM)
    annual performance documents for the years 2019, 2020, 2021, and 2022. Anything outside of
    this scope is not answerable from the documents.

    Question: {question}
    Context: {retrieved_docs}

    Answer:

    Sources:
    - [Name of the document 1]
    - [Name of the document 2]
    """
)

class DocumentGradingResponse(BaseModel):
    """
    Response to the grading of the retrieved documents.
    Returns a single binary value: 0 if context is insufficient, 1 if sufficient.
    """
    is_sufficient: int = Field(
        description="Binary value: 0 if the retrieved context is insufficient to answer the question, 1 if it is sufficient."
    )

DOCUMENT_GRADING_PROMPT = PromptTemplate.from_template(
    """
    You are an assistant for question-answering tasks on Office of Personnel Management (OPM) annual performance documents for the years 2019, 2020, 2021, and 2022. Determine if the provided context is sufficient to answer the question.

    # Steps

    1. **Understand the Question**: Analyze the question to identify what specific information it is asking for.
    2. **Examine the Retrieved Context**: Review all the retrieved documents as a whole to assess if they contain sufficient information to answer the question.
    3. **Evaluate Sufficiency**: Determine if the retrieved context collectively provides enough information based on:
       - **Completeness**: Does the context contain all necessary information to fully answer the question?
       - **Relevance**: Is the information in the context directly related to what the question is asking?
       - **Clarity**: Is the information clear and unambiguous enough to formulate a complete answer?
    4. Make a binary decision:
        - **0 (Insufficient)**: The retrieved context does not contain enough information to answer the question adequately. This could be because:
          - The question asks about information outside the scope of the documents (e.g., years other than 2019-2022)
          - The documents don't contain the specific details requested
          - The information is too vague or incomplete to provide a proper answer
        - **1 (Sufficient)**: The retrieved context contains adequate information to answer the question. The documents have the necessary details to provide a complete and accurate response.

    # Output Format

    Return a single binary value:
    - **0** if the retrieved context is insufficient to answer the question
    - **1** if the retrieved context is sufficient to answer the question

    # Notes

    - Only consider information from documents covering the years 2019, 2020, 2021, and 2022.
    - Questions about years outside this range (e.g., 2029, 2025+) should return 0.
    - Questions about entirely different topics (e.g., NASA, other agencies) should return 0.
    - Be strict: if the context only partially addresses the question or lacks key details, return 0.

    Question: {question}
    Retrieved documents: {retrieved_docs}
    """
)


# NOTE: Descriptive doc-strings and field names are important for the structured output.
class RagGenerationResponse(BaseModel):
    """Response to the question with answer and sources. Sources are
    names of the documents. Sources should be None if the answer is not
    found in the context."""
    answer: str = Field(description="Answer to the question.")
    sources: list[str] = Field(
        description="Names of the documents that contain the answer.",
        default_factory=list
    )
