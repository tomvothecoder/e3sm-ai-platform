# Roadmap

This roadmap lists planned implementation areas for the E3SM AI Platform
prototype. It is not a claim that these capabilities exist today.

## Retrieval and corpus

1. Replace the in-memory lexical store with a durable vector store such as
   pgvector while preserving deterministic tests as the regression baseline.
2. Add hybrid lexical/vector retrieval and reranking behind the existing
   provider-independent interfaces.
3. Expand the curated corpus with versioned source snapshots, automated
   ingestion, freshness checks, and human relevance review.
4. Publish corpus snapshot identifiers and retrieval/chunking/scoring policy
   versions in evaluation artifacts and support metadata.

## External information sources

1. Build an approved web-search provider before enabling live web fallback
   answers.
2. Normalize web citations and provenance before returning web-sourced evidence
   to users or tests.
3. Implement authenticated SimBoard, GitHub/API/MCP, scheduler, and other
   operational connectors only after authorization, audit logging, and
   tool-result provenance are designed.

## Evaluation and quality

1. Expand the question set beyond the current deterministic contract tests.
2. Add retrieval metrics, routing confusion reports, answer/citation quality
   review, and regression thresholds.
3. Keep live LLM and live web behavior out of deterministic CI assertions unless
   separately controlled and recorded.

## Product and platform

1. Add optional conversational context only after defining retention, privacy,
   and evidence-isolation rules.
2. Generalize application registration for additional E3SM assistants without
   coupling corpora, prompts, tools, or evaluation sets.
3. Establish approved secret provisioning, observability, and operational
   runbooks before enabling hosted providers outside controlled environments.
4. Add authentication, authorization, and audit logging before exposing protected
   data or write-capable tools.
