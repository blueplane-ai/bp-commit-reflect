# Contributing to Commit Reflection System

Thank you for your interest in contributing to the Commit Reflection System! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Node.js 18 or higher
- Git
- SQLite (for database storage features)
- Familiarity with TypeScript

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/blueplane-ai/ai-commit-reflect.git
   cd ai-commit-reflect
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Build all packages**
   ```bash
   npm run build
   ```

4. **Run tests**
   ```bash
   npm test
   ```

### Project Structure

```
ai-commit-reflect/
├── packages/
│   ├── cli/                    # Standalone CLI tool
│   │   ├── src/
│   │   │   ├── index.ts        # CLI entry point
│   │   │   ├── session.ts      # Reflection session management
│   │   │   ├── prompts.ts      # Question prompting logic
│   │   │   └── config.ts       # Configuration loading
│   │   └── package.json
│   ├── mcp-server/             # Model Context Protocol server
│   │   ├── src/
│   │   │   ├── index.ts        # MCP server entry point
│   │   │   ├── tools.ts        # MCP tool implementations
│   │   │   └── process-manager.ts  # CLI process coordination
│   │   └── package.json
│   ├── ide-hooks/              # IDE integration hooks
│   │   ├── claude-code/
│   │   │   └── post-tool-use.js
│   │   └── cursor/
│   │       └── afterShellExecution.ts
│   └── shared/                 # Shared types and utilities
│       ├── types/
│       │   ├── reflection.ts   # Core type definitions
│       │   ├── config.ts       # Config type definitions
│       │   └── mcp.ts          # MCP protocol types
│       └── storage/
│           ├── jsonl.ts        # JSONL storage backend
│           ├── sqlite.ts       # SQLite storage backend
│           └── git.ts          # Git commit message backend
├── docs/
│   └── adr/                    # Architecture Decision Records
├── examples/                   # Example configurations and usage
├── tests/                      # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── .config/                    # Default configuration templates
```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, documented code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   npm test
   npm run lint
   npm run type-check
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
   - `feat:` - New features
   - `fix:` - Bug fixes
   - `docs:` - Documentation changes
   - `refactor:` - Code refactoring
   - `test:` - Adding or updating tests
   - `chore:` - Maintenance tasks

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

### TypeScript Guidelines

- Use TypeScript strict mode
- Prefer explicit types over `any`
- Use interfaces for public APIs
- Use type aliases for complex types
- Document public APIs with JSDoc comments

Example:
```typescript
/**
 * Represents a commit reflection session
 */
interface ReflectionSession {
  /** Unique session identifier */
  sessionId: string;

  /** Git commit information */
  commit: CommitInfo;

  /** Collected reflection answers */
  answers: Map<string, unknown>;
}

/**
 * Starts a new reflection session
 * @param commitHash - The git commit hash
 * @returns The initialized session
 */
async function startSession(commitHash: string): Promise<ReflectionSession> {
  // Implementation
}
```

### Formatting

- Use Prettier for code formatting
- 2 spaces for indentation
- Single quotes for strings
- Trailing commas in multi-line structures
- Max line length: 100 characters

Run formatter:
```bash
npm run format
```

## Testing

### Test Structure

- **Unit tests**: Test individual functions and classes in isolation
- **Integration tests**: Test interactions between components
- **E2E tests**: Test complete workflows from CLI to storage

### Writing Tests

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { ReflectionSession } from '../src/session';

describe('ReflectionSession', () => {
  let session: ReflectionSession;

  beforeEach(() => {
    session = new ReflectionSession({
      commitHash: 'abc123',
      project: 'test-project'
    });
  });

  it('should initialize with first question', async () => {
    const response = await session.start();
    expect(response.question.number).toBe(1);
    expect(response.question.id).toBe('ai_synergy');
  });

  it('should validate scale answers', async () => {
    await session.start();

    // Invalid answer
    await expect(
      session.submitAnswer('10')
    ).rejects.toThrow('Answer must be between 1 and 5');

    // Valid answer
    const response = await session.submitAnswer('4');
    expect(response.question.number).toBe(2);
  });
});
```

### Running Tests

```bash
# Run all tests
npm test

# Run specific test file
npm test -- session.test.ts

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

## Documentation

### Code Documentation

- Add JSDoc comments to all public APIs
- Include examples in documentation
- Document complex algorithms inline
- Keep README.md up to date

### Architecture Decision Records

When making significant architectural decisions:

1. Copy `docs/adr/000-template.md`
2. Number it sequentially
3. Fill in all sections:
   - Status
   - Context
   - Decision
   - Consequences
   - Alternatives Considered
4. Submit with your PR
5. Update `docs/adr/README.md` index

## Package-Specific Guidelines

### CLI Package (`packages/cli`)

- Keep CLI focused and lightweight
- Support both interactive and non-interactive modes
- Provide clear error messages
- Include progress indicators for long operations
- Support `--help` and `--version` flags

### MCP Server Package (`packages/mcp-server`)

- Follow MCP specification strictly
- Keep server stateless (state in CLI processes)
- Handle process lifecycle carefully
- Provide clear error responses
- Include session timeout handling

### Shared Package (`packages/shared`)

- Keep shared code minimal and focused
- Avoid circular dependencies
- Export clear, stable interfaces
- Version carefully (breaking changes affect all packages)

## Pull Request Process

1. **Before submitting:**
   - Ensure all tests pass
   - Run linter and fix issues
   - Update documentation
   - Add/update tests for changes
   - Rebase on latest main if needed

2. **PR description should include:**
   - Clear description of changes
   - Motivation for changes
   - Screenshots for UI changes
   - Breaking changes (if any)
   - Related issues (if any)

3. **PR review:**
   - Address reviewer feedback
   - Keep discussions focused
   - Be open to suggestions
   - Update PR as needed

4. **After approval:**
   - Maintainers will merge
   - Delete your feature branch

## Release Process

Releases are managed by maintainers:

1. Version bump following [Semantic Versioning](https://semver.org/)
2. Update CHANGELOG.md
3. Create git tag
4. Publish to npm
5. Create GitHub release

## Getting Help

- **Questions:** Open a GitHub Discussion
- **Bugs:** Open a GitHub Issue
- **Security:** Email security@blueplane.ai (do not open public issue)
- **Chat:** Join our Discord community

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions
- Follow the [Contributor Covenant](https://www.contributor-covenant.org/)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

Thank you for contributing to make developer experiences better!
