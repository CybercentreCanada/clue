
## Contributing

### Branch Strategy

The Clue project follows a Git flow branching model to ensure stable releases and organized development:

#### Main Branches

- **`main`**: Contains production-ready code. All releases are tagged from this branch. Direct commits to `main` are restricted.
- **`develop`**: The integration branch for new features and the primary development branch. All feature branches are created from and merged back into `develop`.

#### Supporting Branches

- **Feature branches**: Created from `develop` for new features or enhancements. Use descriptive names like `feature/add-oauth-provider` or `feature/improve-caching`.
- **Release branches**: Created from `develop` when preparing for a new release (e.g., `release/v2.1.0`). Used for final testing and minor bug fixes.
- **Hotfix branches**: Created from `main` for critical bug fixes that need immediate deployment (e.g., `hotfix/security-patch`).

#### Development Workflow

1. **Feature Development**: Create a feature branch from `develop`
2. **Integration**: Merge completed features into `develop` via pull request
3. **Release Preparation**: Create a release branch from `develop` when ready for release
4. **Production Release**: Merge release branch into both `main` and `develop`, then tag the release
5. **Hotfixes**: If critical issues are found in production, create hotfix branches from `main`

### Pull Request Process

All code changes must go through the pull request process to ensure code quality and maintain project standards:

#### For Contributors with Write Access

1. **Create Feature Branch**: Create a new branch from `develop` with a descriptive name

   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Implement Changes**: Make your changes, following the project's coding standards and including appropriate tests

3. **Open Pull Request**: Create a PR targeting the `develop` branch with:
   - Clear, descriptive title
   - Detailed description of changes
   - Reference to any related issues
   - Screenshots or examples if applicable

#### For External Contributors

1. **Fork Repository**: Fork the Clue repository to your GitHub account

2. **Clone and Setup**: Clone your fork and set up the development environment as described in this guide

3. **Create Feature Branch**: Create a branch from `develop` in your fork

4. **Implement and Test**: Make your changes and ensure all checks pass

5. **Submit Pull Request**: Open a PR from your fork's feature branch to the main repository's `develop` branch

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

- **Merge to Develop**: Once approved and all checks pass, the PR is merged into `develop`
- **Release Cycle**: Features merged into `develop` will be included in the next release when `develop` is merged into `main`
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
