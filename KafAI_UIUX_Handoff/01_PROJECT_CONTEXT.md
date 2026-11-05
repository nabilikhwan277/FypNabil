# KafAI UPKK Project Context

## Product

**KafAI UPKK**  
Tagline: **Learn from every answer.**

Full FYP title:
**Intelligent KAFA Learning Assistant Using Hybrid Large Language Models and Retrieval-Augmented Generation for Student Assessment and Feedback**

## Target users

### Primary student users
- Year 4 KAFA students
- Year 5 KAFA students
- Students preparing for UPKK

### Teacher users
- KAFA teachers who want to review student performance and AI-assisted assessment

## Subject scope

- Tajwid
- Fiqh
- Jawi

## Main problem

Students may know whether an answer is correct or wrong but still not understand:
- what their mistake was,
- why it was wrong,
- how to improve,
- and what they should revise next.

Teachers may also have limited time to provide detailed individual feedback to every student.

## Main solution

KafAI UPKK acts as a personalised KAFA learning assistant.

Typical flow:

Student submits answer
→ relevant KAFA content/rubric is retrieved
→ answer is assessed
→ score is produced
→ mistake is explained
→ personalised feedback is generated
→ next learning action is recommended

## Intended technical direction

- Python
- Streamlit prototype
- Local Llama 3.1 via Ollama
- RAG
- ChromaDB
- Sentence Transformers
- Rubric-based scoring
- ReAct-style reasoning
- Student learning memory
- SQLite
- Optional verification step

## Critical UI principle

Do NOT expose implementation terms such as RAG, embeddings, ChromaDB, ReAct or chain-of-thought to normal student users.

Translate technology into understandable product language, for example:
- “Checked with your KAFA lesson”
- “Personalised from your learning progress”
- “Based on your KAFA material”

## Core student experience

The most important product moment is:

> A student gets an answer wrong and KafAI UPKK helps them understand why.

The feedback experience should follow:

**RESULT → EXPLANATION → ACTION**

## Brand / product personality

KafAI UPKK should feel:
- trustworthy
- calm
- modern
- intelligent
- friendly
- educational
- respectful
- startup-quality

It should NOT feel like:
- a university assignment
- a generic admin dashboard
- a ChatGPT clone
- a mosque event poster
- an overly childish learning game
