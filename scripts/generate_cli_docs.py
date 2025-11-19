#!/usr/bin/env python3
"""
Generate MDX documentation for sup CLI commands using Typer introspection.
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import typer


def clean_help_text(text: str) -> str:
    """Clean and format help text for markdown."""
    if not text:
        return ""

    # Remove ANSI escape codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    text = ansi_escape.sub("", text)

    # Remove Rich markup tags
    rich_markup = re.compile(r"\[/?[^\]]*\]")
    text = rich_markup.sub("", text)

    return text.strip()


def format_help_text_as_markdown(text: str) -> str:
    """Convert help text to well-formatted markdown sections."""
    if not text:
        return ""

    lines = text.split("\n")
    formatted = []
    current_section = None
    in_list = False

    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                formatted.append("")
                in_list = False
            continue

        # Detect section headers (lines ending with colon)
        if line.endswith(":") and not line.startswith("•") and not line.startswith("-"):
            if in_list:
                formatted.append("")
                in_list = False

            # Convert to markdown header
            section_name = line[:-1].strip()
            if section_name:
                formatted.append(f"\n## {section_name}\n")
                current_section = section_name.lower()
            continue

        # Handle bullet points
        if line.startswith("•") or line.startswith("-"):
            if not in_list:
                in_list = True
            item = line[1:].strip() if line.startswith("•") else line[1:].strip()

            # Special formatting for commands
            if current_section and ("setup" in current_section or "tasks" in current_section):
                # Extract command from description
                if ":" in item:
                    desc, cmd = item.split(":", 1)
                    cmd = cmd.strip()
                    if cmd.startswith("sup "):
                        formatted.append(f"- **{desc.strip()}**: `{cmd}`")
                    else:
                        formatted.append(f"- **{desc.strip()}**: {cmd}")
                else:
                    formatted.append(f"- {item}")
            else:
                formatted.append(f"- {item}")
            continue

        # Handle step numbers
        step_match = re.match(r"Step (\d+):\s*(.+)", line)
        if step_match:
            if not in_list:
                in_list = True
            step_num = step_match.group(1)
            step_content = step_match.group(2)
            if " - " in step_content:
                cmd, desc = step_content.split(" - ", 1)
                formatted.append(f"{step_num}. **{desc.strip()}**: `{cmd.strip()}`")
            else:
                formatted.append(f"{step_num}. {step_content}")
            continue

        # Regular text
        if in_list:
            formatted.append("")
            in_list = False
        formatted.append(line)

    return "\n".join(formatted)


def extract_command_info(app: typer.Typer, command_path: List[str] = None) -> Dict[str, Any]:
    """Extract command information from a Typer app."""
    if command_path is None:
        command_path = []

    commands = {}

    # Get the underlying Click group
    click_group = typer.main.get_group(app)

    # Extract subcommands
    if hasattr(click_group, "commands"):
        for name, cmd in click_group.commands.items():
            full_path = command_path + [name]

            # Get command help
            help_text = cmd.help or ""

            # Get parameters (options and arguments)
            params = []
            for param in cmd.params:
                param_info = {
                    "name": param.name,
                    "opts": getattr(param, "opts", []),
                    "type": str(param.type),
                    "required": getattr(param, "required", False),
                    "default": getattr(param, "default", None),
                    "help": getattr(param, "help", "") or "",
                    "is_flag": getattr(param, "is_flag", False),
                    "multiple": getattr(param, "multiple", False),
                }
                params.append(param_info)

            commands[name] = {
                "name": name,
                "path": full_path,
                "help": clean_help_text(help_text),
                "params": params,
                "subcommands": {},
            }

            # Check if this command has subcommands (is a group)
            if hasattr(cmd, "commands"):
                for sub_name, sub_cmd in cmd.commands.items():
                    commands[name]["subcommands"][sub_name] = {
                        "name": sub_name,
                        "help": clean_help_text(sub_cmd.help or ""),
                    }

    return commands


def format_option_table(params: List[Dict[str, Any]]) -> str:
    """Format command parameters as a markdown table."""
    if not params:
        return "_No options available_"

    # Filter out help option
    params = [p for p in params if p["name"] != "help"]

    if not params:
        return "_No additional options_"

    lines = []
    lines.append("| Option | Type | Required | Default | Description |")
    lines.append("|--------|------|----------|---------|-------------|")

    for param in params:
        opts = (
            ", ".join(f"`{opt}`" for opt in param["opts"])
            if param["opts"]
            else f"`{param['name']}`"
        )

        # Clean up type representation
        type_str = param["type"]
        if "STRING" in type_str:
            type_str = "text"
        elif "INT" in type_str:
            type_str = "integer"
        elif "BOOL" in type_str or param["is_flag"]:
            type_str = "flag"
        elif "Choice" in type_str:
            # Extract choices from the type string
            match = re.search(r"\[(.*?)\]", type_str)
            if match:
                type_str = f"choice: {match.group(1)}"
        else:
            type_str = type_str.lower()

        required = "✓" if param["required"] else ""
        default = f"`{param['default']}`" if param["default"] not in [None, "", False] else "-"
        help_text = param["help"].replace("|", "\\|")

        lines.append(f"| {opts} | {type_str} | {required} | {default} | {help_text} |")

    return "\n".join(lines)


def generate_command_mdx(command: Dict[str, Any], is_subcommand: bool = False) -> str:
    """Generate MDX content for a command."""
    name = " ".join(command["path"]) if command.get("path") else command["name"]

    # Extract clean description for frontmatter
    clean_desc = ""
    if command["help"]:
        clean_desc = (
            clean_help_text(command["help"]).split("\n")[0]
            if command["help"]
            else "CLI command documentation"
        )
        # Remove emoji and take first sentence
        clean_desc = re.sub(r"[^\w\s-]", "", clean_desc).strip()
        if "." in clean_desc:
            clean_desc = clean_desc.split(".")[0]
        clean_desc = clean_desc[:100] + "..." if len(clean_desc) > 100 else clean_desc

    # Build the MDX frontmatter
    frontmatter = f"""---
title: "sup {name}"
description: "{clean_desc or "CLI command documentation"}"
---"""

    # Build the content
    content_parts = [frontmatter, ""]

    # Add formatted description if available
    if command["help"]:
        formatted_help = format_help_text_as_markdown(clean_help_text(command["help"]))
        if formatted_help:
            content_parts.append(formatted_help)
            content_parts.append("")

    # Usage section
    content_parts.append("## Usage")
    content_parts.append("")
    content_parts.append("```bash")

    if command.get("subcommands"):
        content_parts.append(f"sup {name} [COMMAND] [OPTIONS]")
    else:
        content_parts.append(f"sup {name} [OPTIONS]")
    content_parts.append("```")
    content_parts.append("")

    # Subcommands section (if any)
    if command.get("subcommands"):
        content_parts.append("## Subcommands")
        content_parts.append("")
        content_parts.append("| Command | Description |")
        content_parts.append("|---------|-------------|")
        for sub_name, sub_info in command["subcommands"].items():
            desc = clean_help_text(sub_info["help"]).split(".")[0] if sub_info["help"] else ""
            content_parts.append(f"| `sup {name} {sub_name}` | {desc} |")
        content_parts.append("")

    # Options section
    if command.get("params"):
        content_parts.append("## Options")
        content_parts.append("")
        content_parts.append(format_option_table(command["params"]))
        content_parts.append("")

    # Examples section
    content_parts.append("## Examples")
    content_parts.append("")
    content_parts.append("import { Tabs, TabItem } from '@astrojs/starlight/components';")
    content_parts.append("")
    content_parts.append("<Tabs>")

    # Generate contextual examples based on command
    if "workspace" in name:
        content_parts.append('  <TabItem label="List workspaces">')
        content_parts.append("    ```bash")
        content_parts.append("    sup workspace list")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
        content_parts.append('  <TabItem label="Set active workspace">')
        content_parts.append("    ```bash")
        content_parts.append("    sup workspace use 123")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
    elif "chart" in name:
        content_parts.append('  <TabItem label="List charts">')
        content_parts.append("    ```bash")
        content_parts.append("    sup chart list --mine")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
        content_parts.append('  <TabItem label="Pull charts">')
        content_parts.append("    ```bash")
        content_parts.append("    sup chart pull --ids 123,456")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
    elif "sql" in name:
        content_parts.append('  <TabItem label="Run query">')
        content_parts.append("    ```bash")
        content_parts.append('    sup sql "SELECT * FROM users LIMIT 10"')
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
        content_parts.append('  <TabItem label="Export to JSON">')
        content_parts.append("    ```bash")
        content_parts.append('    sup sql "SELECT * FROM sales" --json > results.json')
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
    else:
        # Generic example
        content_parts.append('  <TabItem label="Basic usage">')
        content_parts.append("    ```bash")
        content_parts.append(f"    sup {name}")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")

    content_parts.append("</Tabs>")
    content_parts.append("")

    return "\n".join(content_parts)


def capture_sup_output():
    """Run sup command and capture its output."""
    import os

    # Set consistent terminal width to match CI environment
    env = os.environ.copy()
    env["COLUMNS"] = "80"  # Standard terminal width for consistent output

    try:
        result = subprocess.run(["sup"], capture_output=True, text=True, timeout=5, env=env)
        return result.stdout
    except FileNotFoundError:
        # Try python module if sup not in PATH
        try:
            result = subprocess.run(
                ["python", "-m", "sup.main"], capture_output=True, text=True, timeout=5, env=env
            )
            return result.stdout
        except Exception:
            print("Warning: Could not run sup command, using fallback content")
            return None


def generate_index_mdx():
    """Generate the index.mdx content with hero section from actual sup output."""
    # Capture actual sup output
    sup_output = capture_sup_output()

    # Parse output to build hero HTML
    hero_html = ""
    capabilities = []

    if sup_output:
        lines = sup_output.split("\n")
        html_lines = []

        for line in lines:
            if not line:
                continue

            # ASCII art (contains box drawing characters)
            if "███" in line or "██╔" in line or "╚══" in line or "██║" in line:
                escaped = line.replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(
                    f'<span style="color: #10B981; font-weight: bold;">{escaped}</span>'
                )

            # Title line (contains emoji)
            elif "🚀" in line:
                escaped = line.replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(
                    f'<span style="color: #f0f0f0; font-weight: 600;">{escaped}</span>'
                )

            # Subtitle lines
            elif "Brought to you" in line or "For power users" in line:
                escaped = line.replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(f'<span style="color: #9CA3AF;">{escaped}</span>')

            # Section headers
            elif line.strip().endswith(":") and not line.strip().startswith("•"):
                html_lines.append("")
                escaped = line.replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(
                    f'<span style="color: #60A5FA; font-weight: 500;">{escaped}</span>'
                )

            # Bullet points - extract capabilities
            elif line.strip().startswith("•"):
                escaped = line.replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(f'<span style="color: #D1D5DB;">{escaped}</span>')
                # Also save the capability for feature cards
                capabilities.append(line.strip()[1:].strip())

            # Other text
            elif line.strip():
                escaped = line.replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(f'<span style="color: #9CA3AF;">{escaped}</span>')

        # Build the hero HTML with heavy box shadow
        hero_html = "\n".join(html_lines)
    else:
        # Fallback content
        banner_style = 'style="color: #10B981; font-weight: bold;"'
        hero_html = f"""<span {banner_style}>██ ███████╗██╗   ██╗██████╗ ██╗</span>
<span {banner_style}>██ ██╔════╝██║   ██║██╔══██╗██║</span>
<span {banner_style}>   ███████╗██║   ██║██████╔╝██║</span>
<span {banner_style}>   ╚════██║██║   ██║██╔═══╝ ╚═╝</span>
<span {banner_style}>   ███████║╚██████╔╝██║     ██╗</span>
<span {banner_style}>   ╚══════╝ ╚═════╝ ╚═╝     ╚═╝</span>

<span style="color: #f0f0f0; font-weight: 600;">🚀 'sup! - the official Preset CLI 📊</span>
<span style="color: #9CA3AF;">   Brought to you and fully compatible with Preset</span>
<span style="color: #9CA3AF;">   For power users and AI agents</span>"""

        capabilities = [
            "Run any SQL through Superset's data access layer - "
            "get results as rich table, CSV, YAML or JSON",
            "Backup and restore charts, dashboards, and datasets with full dependency tracking",
            "Synchronize assets across Superset instances with Jinja2 templating for customization",
            "Enrich metadata to/from dbt Core/Cloud - more integrations to come",
            "Automate workflows and integrate with CI/CD pipelines",
            "Perfect for scripting and AI-assisted data exploration",
        ]

    # Properly indent the hero HTML for YAML literal scalar
    hero_html_indented = "\n".join(
        "      " + line if line else "" for line in hero_html.split("\n")
    )

    # Terminal styles split for readability
    shadow_style = (
        "box-shadow: 0 40px 80px -20px rgba(0, 0, 0, 0.8), "
        "0 15px 35px -15px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(0, 0, 0, 0.15); "
    )
    terminal_bg = "background: linear-gradient(to bottom, #1a1a1a, #0f0f0f);"
    header_bg = "background: linear-gradient(to right, #2d2d2d, #1a1a1a);"
    font_stack = "'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace"
    code_font = (
        "'Cascadia Code', 'JetBrains Mono', 'SF Mono', "
        "'Monaco', 'Inconsolata', 'Fira Code', monospace"
    )

    # Generate the index.mdx content
    mdx = f"""---
title: Welcome to sup CLI
description: Beautiful, modern interface for Apache Superset and Preset workspaces
template: splash
hero:
  tagline: The official Preset CLI with a git-like interface for managing your analytics assets
  image:
    html: |
      <div style="position: relative; margin: 2rem auto; max-width: 900px;">
        <div style="{shadow_style}border-radius: 12px; overflow: hidden; {terminal_bg}">
          <div style="padding: 0.5rem 1rem; {header_bg} border-bottom: 1px solid #333; display: flex; align-items: center; gap: 0.5rem;">
            <div style="width: 12px; height: 12px; border-radius: 50%; background: #ff5f57;"></div>
            <div style="width: 12px; height: 12px; border-radius: 50%; background: #ffbd2e;"></div>
            <div style="width: 12px; height: 12px; border-radius: 50%; background: #28ca42;"></div>
            <span style="margin-left: auto; font-family: {font_stack}; font-size: 0.75rem; color: #666;">$ sup</span>
          </div>
          <pre style="margin: 0; padding: 2rem; font-family: {code_font}; font-size: 0.875rem; line-height: 1.5; color: #e5e5e5; overflow-x: auto; background: transparent;">
{hero_html_indented}
          </pre>
        </div>
      </div>
  actions:
    - text: Quick Start
      link: introduction/
      icon: right-arrow
      variant: primary
    - text: View Commands
      link: commands/workspace/
      icon: external
---

import {{ Card, CardGrid }} from '@astrojs/starlight/components';

## Features

<CardGrid>
  <Card title="SQL Execution" icon="seti:sql">
    Run any SQL through Superset's data access layer with multiple output formats
  </Card>
  <Card title="Asset Management" icon="github">
    Pull, push, and sync charts, dashboards, and datasets with dependency tracking
  </Card>
  <Card title="Cross-Workspace Sync" icon="rocket">
    Seamlessly move assets between environments with Jinja2 templating
  </Card>
  <Card title="Enterprise Ready" icon="setting">
    JWT authentication, multi-workspace support, and team management
  </Card>
</CardGrid>

## Why sup?

"""

    # Add capabilities as feature bullets
    for capability in capabilities[:6]:
        if " - " in capability:
            parts = capability.split(" - ", 1)
            mdx += f"- **{parts[0].strip()}** - {parts[1].strip()}\n"
        else:
            mdx += f"- {capability}\n"

    mdx += """
## Quick Example

```bash
# Set your workspace
sup workspace use 123

# Pull your charts  
sup chart pull --mine

# Run SQL queries
sup sql "SELECT COUNT(*) FROM users"

# Push to another workspace
sup chart push --workspace-id 456
```

## Getting Started

Start with our [introduction](/introduction/) to understand sup's core concepts, then follow the [installation guide](/installation/) to get up and running.
"""

    return mdx


def generate_docs():
    """Main function to generate documentation."""
    # Import the sup CLI app
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    try:
        from sup.main import app
    except ImportError as e:
        print(f"Error importing sup CLI: {e}")
        print("Make sure the sup package is installed with: pip install -e .")
        return

    # Create output directories
    docs_dir = Path(__file__).parent.parent / "docs-site" / "src" / "content" / "docs"
    commands_dir = docs_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    # Generate index.mdx with hero section from actual sup output
    print("Running 'sup' command to generate hero section...")
    index_file = docs_dir / "index.mdx"
    index_content = generate_index_mdx()
    index_file.write_text(index_content)
    print(f"✓ Generated: {index_file.relative_to(Path.cwd())}")

    # Extract command information
    print("\nExtracting command information from sup CLI...")
    commands = extract_command_info(app)

    # Generate MDX files for each command
    for cmd_name, cmd_info in commands.items():
        output_file = commands_dir / f"{cmd_name}.mdx"
        mdx_content = generate_command_mdx(cmd_info)

        output_file.write_text(mdx_content)
        print(f"✓ Generated: {output_file.relative_to(Path.cwd())}")

    print("\n✅ Command documentation generation complete!")
    print(f"📁 Generated {len(commands)} command reference pages")
    print("\nTo view the docs locally:")
    print("  cd docs-site")
    print("  npm run dev")


if __name__ == "__main__":
    generate_docs()
