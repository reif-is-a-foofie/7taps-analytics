# Tarball Cleanup Plan
_Last updated: 2025-11-08_

This document captures the highest-impact actions we can take to shrink the size of the 7taps-analytics distribution tarball. It will be executed by a follow-up agent; all commands assume the repo root at `/Users/reif/Documents/POL/7taps-analytics`.

## 1. Size Snapshot

| Path / Item | Approx. Size | Notes |
| --- | --- | --- |
| `.git/` | 168 MB | Large binary history, mostly repeated PDF revisions. |
| `Lessons Map/` | 167 MB | 15 PDF lesson handouts ranging from 4–25 MB each. |
| Everything else (code, docs, scripts) | < 5 MB combined | Minor compared to the two items above. |

The tarball is ~339 MB because it packages both working tree binaries and the bloated `.git` directory. Removing or externalizing the lessons content and keeping VCS metadata out of the archive will drop the tarball well below 50 MB.

## 2. Recommended Cleanup (High Level)

1. **Offload or compress `Lessons Map/` assets.** Host PDFs in object storage (GCS/S3) or ship optimized versions only when needed.
2. **Rewrite Git history to drop legacy binaries.** Use BFG or `git filter-repo` so `.git/` stops carrying 160 MB of binary diffs.
3. **Deduplicate CSV exports.** `users_extracted.csv` appears twice (repo root and `Lessons Map/`). Keep only the canonical copy or regenerate on demand.
4. **Exclude secrets and generated artifacts from archives.** Ensure `.env`, `google-cloud-key.json`, `archive/`, etc. never land in distribution bundles.
5. **Adopt an explicit packaging command.** Use `git archive` or `tar --exclude` to guarantee `.git/` and heavyweight folders stay out.

## 3. Detailed Tasks for the Follow-Up Agent

### 3.1 Externalize or Compress `Lessons Map/`
- [ ] Move `Lessons Map/` out of the repo (e.g., to `gs://7taps-assets/lessons-map/`) and replace the folder with lightweight download manifests.
- [ ] Add `Lessons Map/` to `.gitignore` and `.dockerignore` once the assets live elsewhere.
- [ ] For teams that still need local PDFs, provide a pull script:
  ```bash
  mkdir -p Lessons\ Map
  gsutil -m rsync -r gs://7taps-assets/lessons-map Lessons\ Map
  ```
- [ ] If PDFs must remain in-repo, compress them using Ghostscript (average savings 40–60%):
  ```bash
  for pdf in Lessons\ Map/*.pdf; do
    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/ebook \
       -dNOPAUSE -dQUIET -dBATCH -sOutputFile="${pdf%.pdf}-compressed.pdf" "$pdf" &&
    mv "${pdf%.pdf}-compressed.pdf" "$pdf"
  done
  ```

### 3.2 Clean `.git/` History
- [ ] Create a **fresh bare clone** (`git clone --mirror`) to operate safely.
- [ ] Use [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) or `git filter-repo` to remove `Lessons Map/` and other binaries from history:
  ```bash
  java -jar bfg.jar --delete-folders "Lessons Map" --delete-files "*.pdf" <path-to-mirror>
  ```
- [ ] Run `git reflog expire --expire=now --all && git gc --prune=now --aggressive` inside the mirror.
- [ ] Force-push the cleaned mirror back to the origin if acceptable, or keep the mirror as the new release source.

### 3.3 Deduplicate CSV Data
- [ ] Confirm whether `users_extracted.csv` is required for runtime or just documentation.
- [ ] Keep a single authoritative CSV (preferably under `docs/` or a data bucket).
- [ ] Add `users_extracted.csv` to `.gitignore` once the canonical copy is removed from the repo.
- [ ] If the CSV is derived, document the generation command and omit the file entirely from source control/tarballs.

### 3.4 Harden the Packaging Command
- [ ] Replace any `tar czf 7taps-analytics.tar.gz .` usage with either:
  - `git archive --format=tar.gz -o release.tgz HEAD`, or
  - `tar --exclude='.git' --exclude='Lessons Map' --exclude-from=.gitignore -czf release.tgz .`
- [ ] Optionally create a helper script (e.g., `scripts/build_tarball.sh`) so every release uses the same exclusions.
- [ ] Document the script in `README.md` so manual packaging follows the slimmer process.

### 3.5 Remove Secrets & Stray Files
- [ ] Ensure `.env`, `.env.example`, `.DS_Store`, `google-cloud-key.json`, and `archive/` are excluded via `.gitignore`, `.dockerignore`, and the packaging script.
- [ ] Verify no secret files remain in Git history after running the history rewrite.

## 4. Validation Checklist
- [ ] Run `du -sh .` to confirm the working tree drops below 80 MB after changes.
- [ ] Build a tarball with the new script and record its size (target < 40 MB if PDFs are external, < 120 MB if compressed).
- [ ] Smoke-test any runtime paths that previously read from `Lessons Map/` to ensure they now download assets or handle the missing files gracefully.
- [ ] Update documentation (`README.md`, onboarding guides) with the new asset workflow.

Once these tasks are complete, the tarball will contain only source code plus light documentation, dramatically reducing download and deployment times.
