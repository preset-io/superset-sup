# sup CLI Documentation

[![Built with Starlight](https://astro.badg.es/v2/built-with-starlight/tiny.svg)](https://starlight.astro.build)

Documentation website for sup CLI - a beautiful, modern interface for Apache Superset and Preset workspaces.

## 🏗️ Architecture

This documentation site uses a hybrid approach:

- **Auto-generated**: Command reference pages from sup CLI using Typer introspection
- **Handwritten**: Guides, tutorials, and conceptual documentation
- **Theme**: starlight-theme-rapide with emerald green branding

## 🚀 Project Structure

```
docs-site/
├── src/
│   ├── content/
│   │   └── docs/
│   │       ├── commands/          # Auto-generated CLI command docs
│   │       ├── config/            # Configuration guides
│   │       ├── guides/            # User guides and tutorials
│   │       ├── index.mdx          # Homepage
│   │       ├── introduction.md    # Getting started
│   │       ├── installation.md    # Installation guide
│   │       └── quick-start.md     # Quick start guide
│   └── content.config.ts
├── astro.config.mjs               # Starlight + theme configuration
└── package.json
```

## 🧞 Commands

All commands are run from the docs-site directory:

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Installs dependencies                            |
| `npm run dev`             | Starts local dev server at `localhost:4321`      |
| `npm run build`           | Build production site to `./dist/`               |
| `npm run preview`         | Preview build locally before deploying           |

## 🔄 Auto-Generation

Command documentation is automatically generated from the sup CLI:

```bash
# From project root
python scripts/generate_cli_docs.py
```

This extracts command information from Typer and generates MDX files in `src/content/docs/commands/`.

## 🎨 Theme

Uses [starlight-theme-rapide](https://github.com/HiDeoo/starlight-theme-rapide) with emerald green accent colors:

```js
starlightThemeRapide({
  starlightConfig: {
    accent: { 200: '#a7f3d0', 600: '#10b981', 900: '#047857', 950: '#022c22' }
  }
})
```

## 🚀 Deployment

Deployed automatically via GitHub Actions when:
- CLI source code changes (`src/sup/**/*.py`)
- Documentation changes (`docs-site/**`)
- Documentation generator changes (`scripts/generate_cli_docs.py`)

## 📝 Contributing

1. **CLI Commands**: Automatically generated - edit source code and docstrings
2. **Guides**: Edit files in `src/content/docs/guides/`
3. **Configuration**: Edit files in `src/content/docs/config/`
4. **Getting Started**: Edit `introduction.md`, `installation.md`, `quick-start.md`
