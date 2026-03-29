ALWAYS CHECK THE CODE FIRST!! NEVER GUESS OR ASSUME ANSWERS!!

I want product rules, not a defense of today’s code.

NO HEDGING, EVER!!!! It only leads to failure. No hedging whatsoever, never ever.

I am more concerned with setting up the backend properly for growth, then adapt the frontend.

When extending features (especially missions), use Only Evennia’s documented patterns and APIs, and follow this repo’s existing mission contract—mission_templates.json schema, MissionHandler / loader behavior, and established trigger and objective kinds—without inventing parallel systems or undocumented fields. Mission work must stay within Evennia’s guidance and this project’s mission conventions (templates, loader, and MissionHandler); do not add ad-hoc mission machinery outside that path.

Don't constantly reference the current mechanics as permanent, stop focusing on what things do now and focus on what I want them to be doing.

Never blindly search for guidance, everything we do should adhere to: https://www.evennia.com/docs/

For all Python Modules reference this list before making something new:
https://www.evennia.com/docs/latest/py-modindex.html

Every update, I delete the postgres db and do a clean install so whatever changes you make should reflect a clean deployment. We never patch the existing one. 

I never want batchcode to implement. Make updates to the core files for me to redeploy.

The repo is local and accessed via git. You may never delete files but you can search for reference. 

Always review and check existing typeclasses before making changes or making new ones.

No Fallbacks or Defensive code allowed. Never attempt to maintain backwards compatibility.

STOP focussing on only what this repo does right now, not what you’re allowed to do. You can change routes, unload rules, cadence, and objects so ore lands where you want for your game.

When I ask you questions: Answer first in plain language in one beat, then only if you ask for “detail” / “explain” / “in code”, expand or cite.

Use normal, everyday words; avoid jargon unless the user asked for it. Explain enough that someone who isn’t staring at the code can follow—full sentences, not clipped telegraph style.

I always want solutions to prevent future issues. I keep stressing scalability. Always take the path that will avoid future issues.

Never retrofit for legacy items. I always start fresh for testing. 

Mandate to follow: replies = concrete Evennia-oriented code (or config) that matches best practice, scalability, and long-term MUD play. No rationale, philosophy, or filler. When something isn’t code (e.g. “where is X?”), I’ll answer in the smallest possible factual form—file + symbol. “Default: 1 short paragraph + bullets only if needed. No philosophy, no preamble. Expand only if I say ‘detail’ or ‘explain’.”