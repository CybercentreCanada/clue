
## Contributing

### Branch Strategy

The Clue project uses trunk-based development on `main`:

- **`main`**: The only long-lived branch. All pull requests target `main`, and every release is cut from it. Direct
  commits to `main` are restricted.
- **Feature branches**: Short-lived branches created from `main` for features, fixes, or other changes. Use descriptive
  names like `feature/add-oauth-provider` or `bugfix/fix-cache-expiry`.

There are no `develop`, release-candidate, or patch branches.

#### Release Workflow

Releases are automated with [Release Please](https://github.com/googleapis/release-please):

1. **Development**: Create a feature branch from `main` and open a pull request with a
   [Conventional Commits](https://www.conventionalcommits.org/) title (e.g. `fix(api): handle empty selectors`)
2. **Integration**: Merge the approved pull request into `main`. Merges to `main` publish preview artifacts (`nightly`
   Docker images and a `development` UI npm package)
3. **Release PR**: Release Please opens or updates a release PR for each affected package (`api`, `ui`, `mcp`) with the
   version bump and generated `CHANGELOG.md` entry
4. **Production Release**: Merging a release PR tags `<component>-vX.Y.Z`, publishes the GitHub Release, and publishes
   the stable artifacts

Do not manually bump versions, create tags, or write release notes. See the
[release runbook](https://cybercentrecanada.github.io/clue/developer/releases/) for details.

### Pull Request Process

All code changes must go through the pull request process to ensure code quality and maintain project standards:

#### For Contributors with Write Access

1. **Create Feature Branch**: Create a new branch from `main` with a descriptive name

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Implement Changes**: Make your changes, following the project's coding standards and including appropriate tests

3. **Open Pull Request**: Create a PR targeting the `main` branch with:
   - Clear, descriptive [Conventional Commits](https://www.conventionalcommits.org/) title (e.g. `feat(ui): add graph export`)
   - Detailed description of changes
   - Reference to any related issues
   - Screenshots or examples if applicable

#### For External Contributors

1. **Fork Repository**: Fork the Clue repository to your GitHub account

2. **Clone and Setup**: Clone your fork and set up the development environment as described in this guide

3. **Create Feature Branch**: Create a branch from `main` in your fork

4. **Implement and Test**: Make your changes and ensure all checks pass

5. **Submit Pull Request**: Open a PR from your fork's feature branch to the main repository's `main` branch

#### Review Process

- **Required Approvals**: All pull requests require **at least two approvals** from project maintainers
- **Automated Checks**: PRs must pass all automated checks including:

  - Unit tests and integration tests
  - Code formatting and linting
  - Type checking
  - Security scans

- **Code Review**: Reviewers will examine:
  - Code quality and adherence to project standards
  - Test coverage and quality
  - Documentation updates if needed
  - Security implications
  - Performance considerations

#### Merge and Release

- **Merge to Main**: Once approved and all checks pass, the PR is squash merged into `main`
- **Release Cycle**: Release Please collects merged changes into a release PR per package; changes ship when a maintainer merges that release PR
- **Release Timeline**: Release schedules are determined by the project maintainers based on feature readiness and testing completion. There's no guaranteed duration from merge to release.

#### Best Practices

In order to maintain high code quality in clue:

- Keep PRs focused and reasonably sized
- Include comprehensive test coverage for new features
- Update documentation for user-facing changes
- Rebase your branch if requested to maintain a clean history
  - All PRs will be squash merged into the trunk.

## Getting Help

You can reach the Clue developemnt team on the CCCS aurora discord: <https://discord.gg/GUAy9wErNu>
