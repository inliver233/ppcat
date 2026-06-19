# Friend's unflutter outputs (from test1 branch)

These are outputs from test1 branch's analysis using unflutter.
The asm.txt file (127MB) is excluded from this commit due to size.
Get it directly from:
    git show origin/test1:unflutter_dump/asm.txt.gz | gunzip > asm.txt

Files included:
- strings.txt — 32135 isolate strings with ref IDs
- names.txt — 781 VM strings with ref IDs  
- snapshot.json — VM structure info (CIDs, version profile)
- key_addr_context.txt — key address context from test1
