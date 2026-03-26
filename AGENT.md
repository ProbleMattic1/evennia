When extending features (especially missions), use Only Evennia’s documented patterns and APIs, and follow this repo’s existing mission contract—mission_templates.json schema, MissionHandler / loader behavior, and established trigger and objective kinds—without inventing parallel systems or undocumented fields. Mission work must stay within Evennia’s guidance and this project’s mission conventions (templates, loader, and MissionHandler); do not add ad-hoc mission machinery outside that path.

Never blindly search for guidance, everything we do should adhere to: https://www.evennia.com/docs/

For all Python Modules reference this list before making something new:
https://www.evennia.com/docs/latest/py-modindex.html

Every update, I delete the postgres db and do a clean install so whatever changes you make should reflect a clean deployment. We never patch the existing one. 

I never want batchcode to implement. Make updates to the core files for me to redeploy.

The repo is local and accessed via git. You may never delete files but you can search for reference. 

Always review and check existing typeclasses before making changes or making new ones.

No Fallbacks or Defensive code allowed. Never attempt to maintain backwards compatibility.

Always adhere to Evennia best practices for long-term play, flexiblity, and scaling.

Never retrofit for legacy items. I always start fresh for testing. 

Mandate to follow: replies = concrete Evennia-oriented code (or config) that matches best practice, scalability, and long-term MUD play. No rationale, philosophy, or filler. When something isn’t code (e.g. “where is X?”), I’ll answer in the smallest possible factual form—file + symbol. “Default: 1 short paragraph + bullets only if needed. No philosophy, no preamble. Expand only if I say ‘detail’ or ‘explain’.”