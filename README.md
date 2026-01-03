# Vidhi-Sahayak

Vidhi-Sahayak is an offline, Retrieval-Augmented Generation (RAG) based
legal assistant designed to explain India's 2023 criminal law framework
(BNS, BNSS, BSA) using authoritative statutory text.

## Features
- Recursive RAG (Parent–Child retrieval)
- Offline local LLM (Ollama)
- CPU-only execution
- Citation-backed responses
- Dockerized for reproducibility

## Run (MVP)

```bash
docker compose up --build
