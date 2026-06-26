"""Inspect field configuration ("metafields") for each model.

The `metafields/` endpoint is read-only. It returns `field_settings` (the
school's configured fields) and `default_field_settings` (platform defaults),
each keyed by model. Every field has a `label` plus `enabled` / `mandatory`
maps keyed by scope:

    enr   = enrolment form      evt   = event booking
    eoi   = GPA / EOI form      cust  = custom form
    enq   = enquiry form        admin = admin view (enabled only)
"""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

field_settings = client.metafields.field_settings()

print(f"Configured models: {len(field_settings)}")
print("  " + ", ".join(sorted(field_settings)))

# Inspect a single model's fields. `_meta` is metadata, not a field — skip it.
model = "parent" if "parent" in field_settings else next(iter(field_settings))
print(f"\nFields on '{model}':")
for name, cfg in field_settings[model].items():
    if name == "_meta":
        continue
    enabled = cfg.get("enabled", {})
    mandatory = cfg.get("mandatory", {})
    print(
        f"  {cfg.get('label', name):30} "
        f"enrolment: enabled={enabled.get('enr')} mandatory={mandatory.get('enr')}"
    )

# Find every field that is mandatory on the enrolment form, across all models.
print("\nMandatory on the enrolment form:")
for model_name, fields in field_settings.items():
    for name, cfg in fields.items():
        if name == "_meta" or not isinstance(cfg, dict):
            continue
        if cfg.get("mandatory", {}).get("enr"):
            print(f"  {model_name}.{name} ({cfg.get('label')})")
