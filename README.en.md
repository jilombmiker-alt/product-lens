# Product Lens

**Observe a real user journey. Understand the product. Adapt what fits. Build with evidence.**

[中文说明](README.md) · [Skill](skills/product-lens/SKILL.md) · [Example](docs/customer-support-example.md)

Product Lens is an Agent Skill for evidence-led product reverse analysis and implementation planning. Its instructions are written in simplified Chinese. It helps an assistant observe actual product behavior, infer observable responsibilities and mechanisms, adapt useful capabilities to a new goal, and produce a PRD **after** the implementation design.

## Workflow

1. **Reverse analysis:** follow a user scenario through real use or sequential screenshot review. Record actions, feedback, choices, results and gaps. Compare observations with official documentation. Infer roles, tools, data, state and handoffs with explicit evidence levels.
2. **Adaptation, design, then PRD:** assess which capabilities fit the target context, design responsibilities and tools/data/workflows, check the design, then write the PRD.
3. **Core implementation:** build a small real business flow and verify each relevant layer.
4. **Production interaction:** refine the actual target channel, including web, app, chat or message cards.
5. **Deployment and acceptance:** publish only within the authorized scope and verify real behavior, permissions, data and recovery.

Each stage can be requested separately. AI self-review does not replace user acceptance.

## Use cases

AI support and knowledge assistants, media creation, business automation, analytics, office and coding tools. Non-AI products are analyzed through modules and business rules without inventing Agents.

## Install

In Codex with skill-installer available, ask:

```text
Use $skill-installer to install:
https://github.com/jilombmiker-alt/product-lens/tree/main/skills/product-lens
```

Then invoke `$product-lens` in the next task. For other SKILL.md-compatible hosts, install the entire skill directory using the host's documented method. Cross-host operation has not been verified.

## Example request

```text
Use $product-lens to analyze this AI customer-support product.
Follow an employee trying to answer an operational question.
Observe each step before and after acting, preserve evidence, and compare with official documentation.
Infer the product's responsibilities, tools, data and workflow. Separate observed facts, inferences and unknowns.
Stop after the first stage and submit the findings for my review.
```

## Evidence and limits

A screenshot, recording timestamp or actual UI observation must support each claimed journey step. Documentation alone is preparation, not a completed product trial. An assistant role-play is not a user study. Hidden prompts and undocumented backend architecture remain unknown.

This skill depends on the host's browser, runtime, model access and permissions. It does not automatically authorize external writes or deployment. The repository includes structure checks and 40 synthetic handoff checks; it does not claim a production-validated end-to-end product run.

## Checks

```bash
python3 scripts/validate.py
python3 tests/test_handoff.py
```

Python 3.11+, standard library only. See [the Chinese README](README.md) for deliverables, usage examples and contribution guidance.

## License

[MIT](LICENSE). External materials retain their own licenses.
