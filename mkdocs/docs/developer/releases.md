# Release Process

This document describes the steps required to cut a patch (or minor) release for the `ui` or `api` packages in Clue.
The same process applies to both; differences are called out where relevant.

---

## 1. Create a release branch

Branch off `develop` using the naming convention `patch/<version>` (e.g. `patch/1.2.4`):

```bash
git checkout develop
git pull
git checkout -b patch/1.2.4
```

---

## 2. Implement and commit the fixes

Apply the necessary bug fixes or changes on the release branch.
Each logical fix should be its own commit with a conventional commit message, e.g.:

```
fix(ui): onComplete not called for async (pending) actions
fix(ui): duplicate key in executeAction
```

---

## 3. Add changelog entries

Update the relevant release notes file before merging:

- **UI changes** → `mkdocs/docs/releases/ui.md`
- **API changes** → `mkdocs/docs/releases/api.md`

Add a new version section at the top of the file, following the existing format:

```markdown
## `v1.2.4`

- **Async Action `onComplete` Callback** *(bugfix)*: Description of the fix.
- **Duplicate Key in `executeAction`** *(bugfix)*: Description of the fix.
```

Commit the changelog alongside the last fix, or as a dedicated commit:

```
chore(docs): add v1.2.4 release notes
```

---

## 4. Open a pull request

Open a PR from `patch/<version>` targeting `develop`.
Title convention: `release: ui@1.2.4` or `release: api@1.2.4`.

- Ensure all CI checks pass.
- Get the PR reviewed and approved.

---

## 5. Merge the pull request

Merge the PR into `develop` once approved. Prefer a **squash merge** for patch releases to keep the history clean, or a **merge rebase** if individual commits are meaningful.

---

## 6. Tag the release commit

After merging, check out and pull `develop`, then tag the merge commit:

```bash
git checkout develop
git pull
git tag v1.2.4-ui       # or v1.5.0-api
git push --tags
```

Tag naming convention: `v<version>-<package>` (e.g. `v1.2.4-ui`, `v1.5.0-api`).

---

## 7. Publish a GitHub Release

1. Navigate to **Releases → Draft a new release** on GitHub.
2. Select the tag created in step 6.
3. Set the release title to match the tag (e.g. `v1.2.4-ui`).
4. Copy the corresponding version section from the release notes file (`ui.md` or `api.md`) into the release description.
5. Publish the release.

---

## Version numbering

Follow [Semantic Versioning](https://semver.org/):

| Change type | Version bump | Example |
|---|---|---|
| Bug fix, small improvement | Patch (`x.y.Z`) | `1.2.3` → `1.2.4` |
| New backward-compatible feature | Minor (`x.Y.0`) | `1.2.4` → `1.3.0` |
| Breaking change | Major (`X.0.0`) | `1.3.0` → `2.0.0` |
