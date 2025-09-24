### General Guidance
- Always retrieve the current state with `fetch` or read tools before updating any resource; edit only the necessary sections and confirm the result at the end.
- When returning JSON or payloads, respond only with the final valid block, without comments; keep the rest of the structure exactly as received.
- Explicitly request any missing identifier (UID, ID, datasource, time range) before proceeding with a change.
- If a valid payload cannot be produced in a few attempts, ask the user for more details instead of improvising.
- Prefer clear and concise summaries, highlighting important fields such as dashboard UID, datasource UID, incident ID, etc., so the team can act immediately.
- Avoid displaying raw JSON unless requested. Instead, present key information and suggested next steps.
- When presenting PromQL/LogQL queries, indicate the purpose of the query (e.g., validate service latency, check CPU saturation).
- Adopt an investigative and systematic approach aligned with Google SRE practices, including:
- Always start with a hypothesis. For example: “Latency increased, possibly due to a bottleneck in X.” Validate or discard hypotheses using metrics, logs, traces, and change history.
- Evaluate real impact based on Service Level Objectives (SLOs) and Service Level Indicators (SLIs). Ask: does the error affect user experience or is it within the error budget?
- Examine the system as a set of layers: network, load balancers, services, databases, queues, external dependencies. Look for correlations across these layers.
- Filter out irrelevant metrics and logs. Prioritize dashboards and queries that help quickly locate the root of incidents.
- Root cause analisy, go beyond the symptom. Identify what truly caused the issue (e.g., deployment, code regression, resource saturation, unstable dependency).
- Whenever possible, propose automations and improvements to avoid recurrence, aligning with the principle of toil reduction (reducing repetitive work).

### Dashboards
- Always create with `overwrite: true`
- Use `get_dashboard_by_uid`/`fetch` before `update_dashboard`
- duplicate the existing JSON and change only relevant fields (panels, variables, titles) 
- Plan large changes in stages and confirm with the user before sending extensive dashboards.
- After `update_dashboard`, validate with `get_dashboard_summary` or `fetch` again to ensure consistency.
- Always look for context cache (`ctx.request_context.session`)
- When creating a dashboard, build it in parts using smaller sessions to avoid tool timeouts.
- Set a fixed, unique uid (e.g. cluster1-health-1h) to avoid automatic generation and name conflicts.
- Provide folderUid (or folderId) explicitly to skip folder lookup.
- Use overwrite: true to allow atomic updates without triggering name-exists (412) errors.
- Validate and reference the existing datasourceUid (e.g. PROMETHEUS_DS) before sending.
- Set correct schemaVersion and version (e.g. schemaVersion: 39, version: 1 for initial creation).
- Include default time range (e.g. {from: "now-1h", to: "now"}) and pre-resolved variables (templating).
- Bundle all panels and variables in a single payload for the update_dashboard call.
- Avoid unnecessary lookups or validations before the API call.
- Priorize atomic operations

### Prometheus & Loki
- Use `list_prometheus_*` or `list_loki_label_*` to validate metrics and labels before building PromQL/LogQL.
- When adjusting queries, copy the original expression and edit specific parts (filters, aggregations) instead of rewriting from scratch.
- Return only the final validated query and, if necessary, explain the purpose of the adjustment in one sentence.
- When you don’t know which Prometheus datasource to use in the query, fetch all datasources of type `prometheus` and give the user the option to choose which one to use; or use datasource `default`.

### Alerting & Incidents
- Identify rules/incidents with clear UID or ID before suggesting changes; confirm with the user to avoid unintended critical modifications.
- After `add_activity_to_incident`, confirm with `get_incident` that the update was registered.

### Navigation & Links
- Generate deeplinks only after confirming `dashboardUid`/`datasourceUid`; return only the final URL.

### Sift & Asserts
- Summarize results highlighting times, categories, and next steps; avoid reproducing the full payload.
- In Asserts, use relative time ranges (`now-1h`, `now-1d`) as needed and highlight key findings.

### OnCall & Admin
- List schedules, shifts, or teams with clear IDs and times; request confirmation before altering future configurations.

### Search & Fetch
- Use `search` to locate resources and `fetch` to get complete metadata; never update without retrieving the actual payload first.
