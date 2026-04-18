# typescript-quality

[![CI](https://github.com/wrxck/typescript-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/wrxck/typescript-quality/actions/workflows/ci.yml)

Enforce TypeScript quality standards in Claude Code sessions.

## What it checks

- No `any` type usage (explicit any, cast to any, any in generics)
- Prefer named exports over default exports (with Next.js exceptions)
- No `console.log` or `debugger` statements in production code (test files exempt)

## Installation

```
claude plugin marketplace add wrxck/claude-plugins
claude plugin install typescript-quality@wrxck-claude-plugins
```
