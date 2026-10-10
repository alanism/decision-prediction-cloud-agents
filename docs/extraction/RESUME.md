# Resume the independent cloud extraction

Read tasks.json and verification/STATUS.md first. This extraction has a fixed ten-task denominator, independent of the prior PR2 implementation board. Never copy a prior percentage or historical test count into a current pass.

1. Check release-tree status and UPSTREAM.json source/patch manifest.
2. Rerun affected portable and inventory tests from this tree; retain exact commands and results.
3. Fresh-install into a new directory, relocate it, and invoke from an unrelated working directory.
4. Check immutable report storage, synthetic image-negative gate and any separately authorized actual-image handoff.
5. Keep full original pytest, browser visual/interaction, native OAI and secondary-host acceptance gaps explicit.
6. Independent review and publication need separate evidence. The parent handles repository creation/publication; this tree does not authorize changing upstream main or merging/closing its PRs.

Use scripts/update_extraction_board.py to regenerate KANBAN.html from tasks.json. Mark Done only with evidence. Do not remove blocked tasks to improve the percentage. Runtime private inputs and report outputs remain outside the release tree.
