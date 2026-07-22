# LLM and Human Division of Labor

This product should be designed as a mostly-LLM loop with small, high-leverage human checkpoints.

## Operating principle

LLMs do high-volume drafting, comparison, extraction, and critique. Humans decide claims, risk, customer fit, and final delivery.

## Division by workflow

| Workflow | LLM owns | Human owns | Required evidence |
|---|---|---|---|
| Market research | Collect pain themes, draft hypotheses, compare offers | Pick target niche and reject weak positioning | Source links, observed competitor screenshots, notes |
| Xiaohongshu content | Generate titles, outlines, posts, comment replies | Publish, observe audience reaction, decide tone | Post URL, impressions, likes, saves, comments, DMs |
| Private chat | Draft qualification questions and reply options | Handle real customer trust-building and price negotiation | Chat summary, customer type, pain, next step |
| Product page | Draft title, detail page, FAQ, disclaimers | Confirm platform category/rule constraints and upload | Page screenshots, category, published URL |
| Data intake | Create checklist, parse sample schemas, detect missing fields | Confirm whether the data can support the promised question | Data inventory, missing-field log |
| Metric governance | Suggest terms, metrics, dimensions, entity relations | Approve business definitions and source authority | Steward note, source reference |
| Diagnosis report | Draft analysis, assumptions, evidence, recommendations | Review correctness and remove overclaims | Report version, review notes |
| Product iteration | Cluster issues, propose backlog, write tasks | Decide weekly priority and pricing changes | AICO daily/weekly, backlog, acceptance results |

## Human checkpoints

Humans must approve before:

1. Publishing claims about customer outcomes.
2. Accepting a customer order when the available data may not support the promised diagnosis.
3. Sending the final report.
4. Using any anonymized customer case in public content.
5. Connecting to a buyer's production system or private platform account.

## LLM checkpoints

Every important output should pass at least three LLM challenge passes:

1. **Feasibility challenge**: can we actually deliver this with current product and human effort?
2. **Truth challenge**: does this claim have evidence, or is it sales fiction?
3. **Conversion challenge**: would a busy small-business owner understand and care?

The Challenger should write objections before the Reviewer approves buyer-facing output.
