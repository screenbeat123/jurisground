# Project origin

JurisGround was extracted and generalized from the verification layer of a larger local-first Polish legal-AI research and drafting system.

The parent system had accumulated deterministic checks around quote recovery, numeric provenance, source IDs, claim-to-evidence support, fail-closed document generation, and synthetic regression tests. JurisGround isolates the reusable part of that work into a small open-source package.

This repository intentionally excludes client material, private datasets, legal corpora, vector databases, user interfaces, and the parent application's document-generation workflow.
