# Clue UI Development Guide

This guide outlines how to set up a development environment for the Clue UI.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- Python 3.10, 3.11, or 3.12 (3.12 recommended) (used in build_scripts )
- Node/NPM (Recommended to be installed using NVM)
- PNPM
- Git

## Development Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/CybercentreCanada/clue.git
cd clue/ui
```

### 2. Install Node/NPM using NVM

If you don't have NPM installed, follow the [official installation guide](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating).

Verify NPM installation:

```bash
npm --version
```

### 3. Install PNPM using NPM

This project uses PNPM to manage dependencies, since it's faster than the default NPM (and corporate proxy networks can be quite slow).

PNPM can simply be installed using NPM:
```bash
npm install -g pnpm
```

### 4. Install Project Dependencies using PNPM

Now that PNPM is installed, you can install the project dependencies:

```bash
pnpm install
```

This will install all dependencies in the node_modules directory.

## Development Workflow

### Starting the Development Server

Start the Clue UI in dev mode:

```bash
pnpm dev
```

### Running Tests

Run tests:

```bash
pnpm test
```

You can also run tests with a prettier terminal UI using this command:

```bash
pnpm test-ui
```

### Additional scripts

For more launch options, see the "scripts" section of the package.json file.

## Troubleshooting



## Getting Help

You can reach the Clue developemnt team on the CCCS aurora discord: <https://discord.gg/GUAy9wErNu>
