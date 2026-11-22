import os

# The E2E suite needs a live stack, so keep it out of the normal pytest run.
if os.environ.get('RUN_E2E') != '1':
    collect_ignore_glob = ['*']
