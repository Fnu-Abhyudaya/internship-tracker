"""TEMPORARY: full dry run (no email, no history update)."""
import asyncio, shutil
from collections import Counter
from . import main as M

posts, stats, issues = asyncio.run(M.run_all_scrapers())
kept = M.deduplicate_within_run(M.final_filter(posts))
path = M.create_excel(kept, issues)
shutil.copy(path, '../../dry_run.xlsx')
print('######## RESULTS ########')
print('sites:', len(stats), 'raw:', len(posts), 'kept:', len(kept))
for c, n in sorted(Counter(p.company for p in kept).items()):
    print(f'  {c}: {n}')
print('ISSUES', len(issues))
for i in issues:
    print(f'  {i.status} | {i.company} | {i.details[:150]!r}')
