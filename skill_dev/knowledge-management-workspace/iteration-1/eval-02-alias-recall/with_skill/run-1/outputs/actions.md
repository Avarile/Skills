## Calls made

1. `cat skill_dev/knowledge-management/SKILL.md` (+ `ls -R` of the skill dir): read the skill instructions.
2. `python3 skill_dev/knowledge-management/scripts/kb.py find kubernetes node labels`: 2 matches (aliases on). K3S - Cheatsheet `rec9TTSDoktu59fT89i` [k3s - operation, 31.4k chars]; Onyx - docker-compose `recrHVpZPhA85MMsXhU` (incidental "kubernetes" in a path, not relevant).
3. `python3 skill_dev/knowledge-management/scripts/kb.py get rec9TTSDoktu59fT89i --toc`: 29-section TOC; relevant sections are "3. Node Management" and "20. Labels, Annotations & Selectors".
4. `python3 skill_dev/knowledge-management/scripts/kb.py get rec9TTSDoktu59fT89i --section "3. Node Management"`: returned the node label/taint/cordon/drain commands. (A trailing `echo ======` in the same shell line failed under zsh; this did not affect the kb.py output.)
5. `python3 skill_dev/knowledge-management/scripts/kb.py get rec9TTSDoktu59fT89i --section "20. Labels, Annotations & Selectors"`: returned the label/selector/annotation commands.
6. `python3 skill_dev/knowledge-management/scripts/kb.py find nodeSelector`: 0 matches.
7. `python3 skill_dev/knowledge-management/scripts/kb.py find node label --type k3s`: 1 match, the same K3S - Cheatsheet `rec9TTSDoktu59fT89i`.

## Proposed writes

none
