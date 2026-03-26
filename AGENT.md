##Never blindly search for guidance, everything we do should adhere to: https://www.evennia.com/docs/

Always refer to local /docs for official guidance.

For all Python Modules reference this list before making something new:
https://www.evennia.com/docs/latest/py-modindex.html

##You must always reference the official documentation, if something is not in there you must stop and ask me for next steps.

Every update I delete the postgres db and do a clean install so whatever changes you make should reflect a clean deployment. We never patch the existing one. 

I never want batchcode to implement. Make updates to the core files for me to redeploy.

The repo is local and accessed via git. You may never delete files but you can search for reference. 

Always review and check existing typeclasses before making changes or making new ones.

No Fallbacks or Defensive code allowed.

Always adhere to Evennia best practices for long-term play, flexiblity, and scaling.

Never retrofit for legacy items. I always start fresh for testing. 