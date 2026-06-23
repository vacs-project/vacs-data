<!-- Delete everything between these markers before submitting. -->
<!-- ===== CONTRIBUTION GUIDELINES (delete this section) ===== -->

> [!WARNING]
> Make sure your dataset is in the correct `dataset/{FIR}/` directory, otherwise CI will not pick it up.

**New FIR?** Please add a small paragraph about your affiliation to the respective FIR to this PR description. We'll be glad to accept your contribution, but would like to ensure our dataset's origin is transparent. Also include a list of others who should be added as maintainers (you should have at least 2 people to review each other's PRs). After the first PR is merged, we'll add you to CODEOWNERS for that FIR so that future changes can be reviewed by you. See [CONTRIBUTING.md](../CONTRIBUTING.md) for full details.

**Existing FIR?** As a dataset maintainer, you are responsible for getting reviews from your fellow CODEOWNERS and merging your own PRs once CI passes. If you need help from the vacs core team, request a review from `@vacs-project/core-maintainers`.

> [!IMPORTANT]
> Please **enable "Allow edits by maintainers"** (checkbox below the description box) so that our formatting bot can push fixes to your branch.

<!-- ===== CONTRIBUTION GUIDELINES (delete everything above) ===== -->

### Description

<!-- What does this PR change and why? -->

### AIRAC dependency

- [ ] This change is **AIRAC-dependent** and should only go live after a specific AIRAC cycle takes effect.

<!-- If checked, add the appropriate airac/XXYY label to this PR (e.g., airac/2604).
     The merge check will block until that cycle's effective date, then pass automatically.
     You can enable auto-merge now -- the PR will merge on its own once the gate opens and CI passes. -->

### Checklist

- [ ] Dataset files are in the correct `dataset/{FIR}/` directory.
- [ ] I have verified the data is correct.
- [ ] If adding a new FIR: CODEOWNERS entry added and maintainer team noted in PR description.
- [ ] If contributing from a fork: "Allow edits by maintainers" is enabled.
