# 0001. Synthetic data only

**Status:** Accepted

## Context

This platform demonstrates governance patterns for AI use in a healthcare research setting. Any
realistic healthcare governance demo is tempted to reach for data that "looks real" to make the
story compelling. That temptation is a liability here: this is a public portfolio repository with
no institutional data-handling controls, no IRB, no BAA, and no legal basis to hold protected
health information (PHI) or any other real patient, clinician, or institutional data.

## Decision

Every dataset, record, and identifier used anywhere in this platform — now and in every future
milestone — will be synthetic. No real patient data, no real clinician data, no real institutional
identifiers, and no data sourced from any real healthcare organisation will be introduced. Where
the platform later needs a research inventory, access logs, or audit events to demonstrate
governance mechanics, those will be generated synthetic data, clearly labelled as such at the
point of generation and in any documentation or report that surfaces them.

This also extends to infrastructure: no real Snowflake account, Fabric tenant, or cloud
environment will be represented as existing or connected. Documentation describing those systems
describes intent, not a live integration.

## Consequences

- The platform can be shared publicly without a data-handling review.
- Any demo, screenshot, or report generated from this platform is a synthetic-data illustration
  of a governance mechanism, not evidence about a real population — this must stay visible in
  labelling, not just true in principle.
- Milestones that would otherwise reach for a "real-looking" public healthcare dataset (e.g. a
  de-identified public dataset) are still out of scope unless a future ADR explicitly revisits
  this decision; the default is fully synthetic generation.
- Some realism is sacrificed (synthetic data rarely reproduces the messiness of real operational
  data), which is an accepted tradeoff against the alternative of handling data this project has
  no basis to hold.
