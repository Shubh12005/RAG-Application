# Guidelines for Anti-Hallucination in RAG Systems

## 1. Core Principle
Retrieval-Augmented Generation systems must never invent facts. When a user asks a question, the LLM must synthesize the answer using **only** the retrieved context passages provided in the prompt.

## 2. Refusal Protocol
If the retrieved chunks do not contain sufficient evidence to answer the query, the system must trigger the canonical refusal sentence:
> "I could not find this information in the uploaded document."

## 3. Provenance and Citation
Every statement made in the answer should correspond to a specific chunk and page reference:
- PDF files: cite the document title and 1-based page number.
- DOCX and Markdown: cite the heading or section name.
- CSV: cite the row numbers and column names.
