# Reusable Prompt: Pizzatorio Continuous AI Status Report

Use this prompt with any AI coding agent:

```text
You are working on the Pizzatorio repository.

Primary context file:
- AI_AGENT_HELPER.md

Instructions:
1) Always read and follow AI_AGENT_HELPER.md before planning or coding.
2) At the start of each response, include a short "Phase" label:
   - Phase: Planning / Building / Stabilizing / Shipping / Next Phase
3) Produce a status report in this exact structure:

STATUS REPORT
- What was done:
  - <completed implementation items>
- What was shipped:
  - <items merged/released and commit or PR reference>
- Bugs fixed:
  - <bug + root cause + fix + validation>
- In progress:
  - <active tasks>
- Blockers/Risks:
  - <technical/product risks>
- Next phase trigger:
  - <condition that moves us to the next phase>
- Next phase plan:
  - <3-7 bullet execution plan>

4) When a new phase is entered, explicitly print:
   NEW PHASE ENTERED: <phase name>
   REASON: <why we moved>

5) Keep implementation aligned with:
   - data-driven systems
   - headless simulation compatibility
   - modular architecture targets
   - recipe/machine/research roadmap

6) If a requested task conflicts with AI_AGENT_HELPER.md, do the user request first and note the conflict.
```

## Optional quick-use variant

```text
Use AI_AGENT_HELPER.md as source of truth.
Give me a STATUS REPORT with:
- What was done
- What was shipped
- Bugs fixed
- In progress
- Blockers/Risks
- Next phase trigger
- Next phase plan

If phase changed, print: NEW PHASE ENTERED + REASON.
```
