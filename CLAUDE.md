# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**#BuildingResilience WhatsApp AI Assistant** for the OAFLAD campaign, built by BOMALAB (CHOMEI COMMERZ LTD). Event date: 17 April 2026, ~1,000 participants. Bilingual FR/EN with PT handled natively by Claude.

This repo was forked from a World Bank WhatsApp-RAG-Example. The new architecture **replaces OpenAI/LangChain RAG with direct Claude API context injection** and **replaces PostgreSQL with Supabase**.

### Target Architecture (being built)
- **LLM:** Anthropic Claude API (direct context injection, not RAG — unless content outgrows context window)
- **Backend:** FastAPI, deployed to Vercel serverless or Railway
- **Database:** Supabase (4 tables: wa_conversations, wa_messages, wa_broadcasts, wa_analytics_daily)
- **Messaging:** Twilio WhatsApp API (Twilio/Meta setup mostly complete)
- **Compliance:** RGPD — sender phone numbers stored as SHA-256 hashes only

### Roadmap Reference
Full roadmap in `BuildingResilience_WhatsApp_Roadmap.pdf.pdf`. Key components:
- **COMP A (Twilio/Meta):** WA-A01 to A06 + A11 done. Remaining: display name, profile, sandbox, templates.
- **COMP B (Backend):** FastAPI scaffold, webhook handler, Claude integration, Supabase logging, rate limiting, error handling, broadcast endpoint, production deploy.
- **COMP C (Knowledge Base):** System prompt design, campaign/event/speaker/FAQ content (mostly blocked on OC content delivery).
- **COMP D (Community):** WhatsApp Community with channels (#Annonces, #Programme, #Réseautage, #Exposition, #Délégation-VIP).
- **COMP E (Testing):** E2E, load (100+ concurrent), edge cases, VIP soft launch, production cutover.

## Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the FastAPI server
uvicorn main:app --reload

# Verify LangChain setup
python basic_chain.py

# Test individual modules (each has if __name__ == '__main__' blocks)
python rag_chain.py
python memory.py
python ensemble.py
python vector_store.py
python local_loader.py
```

No formal test framework is configured. Testing is done via module-level main blocks.

## Environment Variables

**Target (new architecture):** `ANTHROPIC_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_NUMBER`, `SUPABASE_URL`, `SUPABASE_KEY`.

**Legacy (forked repo):** `OPENAI_API_KEY`, `HUGGINGFACEHUB_API_TOKEN`, `DB_USER`, `DB_PASSWORD`.

## Architecture

**Request flow:** Twilio WhatsApp message → FastAPI `/message` endpoint (main.py) → `run_rag_query()` (utils.py) → RAG chain with memory → response stored in PostgreSQL → sent back via Twilio.

**Document pipeline:** PDFs/TXT/CSV loaded (local_loader.py) or web pages fetched (remote_loader.py) → chunked with RecursiveCharacterTextSplitter at 1000 chars (splitter.py) → stored in ChromaDB with OpenAI text-embedding-3-small (vector_store.py).

**Retrieval:** Ensemble retriever (ensemble.py) combines BM25 keyword search (50%) + ChromaDB vector search (50%).

**Chain assembly:** basic_chain.py provides the LLM model → rag_chain.py wraps retriever + prompt + LLM → memory.py adds session-based chat history for multi-turn conversations.

**Persistence:** models.py defines SQLAlchemy `Conversation` table (sender, message, response) on PostgreSQL. Vector DB persisted in `./store/`.

## Key Directories

- `data/` - Production document corpus (WHO disease outbreak PDFs)
- `store/` - ChromaDB vector database files (gitignored)
- `examples/` - Example documents for testing

## Notable Implementation Details

- `vector_store.py` has an `EmbeddingProxy` class that adds 20ms rate-limiting delays between embedding API calls
- RAG prompt comes from LangChain Hub ("rlm/rag-prompt")
- Some dependency versions are pinned due to langchain/streamlit chat history compatibility issues (see langchain-ai/langchain#18834)
- `decouple.config` is used for env var access (not `os.environ`)
