#!/usr/bin/env python3
"""
Generate MDX documentation for sup CLI commands using Typer introspection.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from typer.core import TyperGroup
from typer.models import CommandInfo
from rich.console import Console
from rich.table import Table


def clean_help_text(text: str) -> str:
    """Clean and format help text for markdown."""
    if not text:
        return ""
    
    # Remove ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    
    # Remove Rich markup tags
    rich_markup = re.compile(r'\[/?[^\]]*\]')
    text = rich_markup.sub('', text)
    
    return text.strip()


def format_help_text_as_markdown(text: str) -> str:
    """Convert help text to well-formatted markdown sections."""
    if not text:
        return ""
    
    lines = text.split('\n')
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
        if line.endswith(':') and not line.startswith('•') and not line.startswith('-'):
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
        if line.startswith('•') or line.startswith('-'):
            if not in_list:
                in_list = True
            item = line[1:].strip() if line.startswith('•') else line[1:].strip()
            
            # Special formatting for commands
            if current_section and 'setup' in current_section or 'tasks' in current_section:
                # Extract command from description
                if ':' in item:
                    desc, cmd = item.split(':', 1)
                    cmd = cmd.strip()
                    if cmd.startswith('sup '):
                        formatted.append(f"- **{desc.strip()}**: `{cmd}`")
                    else:
                        formatted.append(f"- **{desc.strip()}**: {cmd}")
                else:
                    formatted.append(f"- {item}")
            else:
                formatted.append(f"- {item}")
            continue
        
        # Handle step numbers
        step_match = re.match(r'Step (\d+):\s*(.+)', line)
        if step_match:
            if not in_list:
                in_list = True
            step_num = step_match.group(1)
            step_content = step_match.group(2)
            if ' - ' in step_content:
                cmd, desc = step_content.split(' - ', 1)
                formatted.append(f"{step_num}. **{desc.strip()}**: `{cmd.strip()}`")
            else:
                formatted.append(f"{step_num}. {step_content}")
            continue
            
        # Regular text
        if in_list:
            formatted.append("")
            in_list = False
        formatted.append(line)
    
    return '\n'.join(formatted)


def extract_command_info(app: typer.Typer, command_path: List[str] = None) -> Dict[str, Any]:
    """Extract command information from a Typer app."""
    if command_path is None:
        command_path = []
    
    commands = {}
    
    # Get the underlying Click group
    click_group = typer.main.get_group(app)
    
    # Extract subcommands
    if hasattr(click_group, 'commands'):
        for name, cmd in click_group.commands.items():
            full_path = command_path + [name]
            
            # Get command help
            help_text = cmd.help or ""
            
            # Get parameters (options and arguments)
            params = []
            for param in cmd.params:
                param_info = {
                    'name': param.name,
                    'opts': getattr(param, 'opts', []),
                    'type': str(param.type),
                    'required': getattr(param, 'required', False),
                    'default': getattr(param, 'default', None),
                    'help': getattr(param, 'help', "") or "",
                    'is_flag': getattr(param, 'is_flag', False),
                    'multiple': getattr(param, 'multiple', False),
                }
                params.append(param_info)
            
            commands[name] = {
                'name': name,
                'path': full_path,
                'help': clean_help_text(help_text),
                'params': params,
                'subcommands': {},
            }
            
            # Check if this command has subcommands (is a group)
            if hasattr(cmd, 'commands'):
                sub_app = typer.Typer()
                for sub_name, sub_cmd in cmd.commands.items():
                    commands[name]['subcommands'][sub_name] = {
                        'name': sub_name,
                        'help': clean_help_text(sub_cmd.help or ""),
                    }
    
    return commands


def format_option_table(params: List[Dict[str, Any]]) -> str:
    """Format command parameters as a markdown table."""
    if not params:
        return "_No options available_"
    
    # Filter out help option
    params = [p for p in params if p['name'] != 'help']
    
    if not params:
        return "_No additional options_"
    
    lines = []
    lines.append("| Option | Type | Required | Default | Description |")
    lines.append("|--------|------|----------|---------|-------------|")
    
    for param in params:
        opts = ', '.join(f"`{opt}`" for opt in param['opts']) if param['opts'] else f"`{param['name']}`"
        
        # Clean up type representation
        type_str = param['type']
        if 'STRING' in type_str:
            type_str = 'text'
        elif 'INT' in type_str:
            type_str = 'integer'
        elif 'BOOL' in type_str or param['is_flag']:
            type_str = 'flag'
        elif 'Choice' in type_str:
            # Extract choices from the type string
            match = re.search(r'\[(.*?)\]', type_str)
            if match:
                type_str = f"choice: {match.group(1)}"
        else:
            type_str = type_str.lower()
        
        required = '✓' if param['required'] else ''
        default = f"`{param['default']}`" if param['default'] not in [None, '', False] else '-'
        help_text = param['help'].replace('|', '\\|')
        
        lines.append(f"| {opts} | {type_str} | {required} | {default} | {help_text} |")
    
    return '\n'.join(lines)


def generate_command_mdx(command: Dict[str, Any], is_subcommand: bool = False) -> str:
    """Generate MDX content for a command."""
    name = ' '.join(command['path']) if command.get('path') else command['name']
    
    # Extract clean description for frontmatter
    clean_desc = ""
    if command['help']:
        clean_desc = clean_help_text(command['help']).split('\n')[0] if command['help'] else 'CLI command documentation'
        # Remove emoji and take first sentence
        clean_desc = re.sub(r'[^\w\s-]', '', clean_desc).strip()
        if '.' in clean_desc:
            clean_desc = clean_desc.split('.')[0]
        clean_desc = clean_desc[:100] + "..." if len(clean_desc) > 100 else clean_desc
    
    # Build the MDX frontmatter
    frontmatter = f"""---
title: "sup {name}"
description: "{clean_desc or 'CLI command documentation'}"
---"""
    
    # Build the content
    content_parts = [frontmatter, ""]
    
    # Add formatted description if available
    if command['help']:
        formatted_help = format_help_text_as_markdown(clean_help_text(command['help']))
        if formatted_help:
            content_parts.append(formatted_help)
            content_parts.append("")
    
    # Usage section
    content_parts.append("## Usage")
    content_parts.append("")
    content_parts.append("```bash")
    
    if command.get('subcommands'):
        content_parts.append(f"sup {name} [COMMAND] [OPTIONS]")
    else:
        content_parts.append(f"sup {name} [OPTIONS]")
    content_parts.append("```")
    content_parts.append("")
    
    # Subcommands section (if any)
    if command.get('subcommands'):
        content_parts.append("## Subcommands")
        content_parts.append("")
        content_parts.append("| Command | Description |")
        content_parts.append("|---------|-------------|")
        for sub_name, sub_info in command['subcommands'].items():
            desc = clean_help_text(sub_info['help']).split('.')[0] if sub_info['help'] else ""
            content_parts.append(f"| `sup {name} {sub_name}` | {desc} |")
        content_parts.append("")
    
    # Options section
    if command.get('params'):
        content_parts.append("## Options")
        content_parts.append("")
        content_parts.append(format_option_table(command['params']))
        content_parts.append("")
    
    # Examples section
    content_parts.append("## Examples")
    content_parts.append("")
    content_parts.append("import { Tabs, TabItem } from '@astrojs/starlight/components';")
    content_parts.append("")
    content_parts.append("<Tabs>")
    
    # Generate contextual examples based on command
    if 'workspace' in name:
        content_parts.append("  <TabItem label=\"List workspaces\">")
        content_parts.append("    ```bash")
        content_parts.append("    sup workspace list")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
        content_parts.append("  <TabItem label=\"Set active workspace\">")
        content_parts.append("    ```bash")
        content_parts.append("    sup workspace use 123")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
    elif 'chart' in name:
        content_parts.append("  <TabItem label=\"List charts\">")
        content_parts.append("    ```bash")
        content_parts.append("    sup chart list --mine")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
        content_parts.append("  <TabItem label=\"Pull charts\">")
        content_parts.append("    ```bash")
        content_parts.append("    sup chart pull --ids 123,456")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
    elif 'sql' in name:
        content_parts.append("  <TabItem label=\"Run query\">")
        content_parts.append("    ```bash")
        content_parts.append('    sup sql "SELECT * FROM users LIMIT 10"')
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
        content_parts.append("  <TabItem label=\"Export to JSON\">")
        content_parts.append("    ```bash")
        content_parts.append('    sup sql "SELECT * FROM sales" --json > results.json')
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
    else:
        # Generic example
        content_parts.append("  <TabItem label=\"Basic usage\">")
        content_parts.append("    ```bash")
        content_parts.append(f"    sup {name}")
        content_parts.append("    ```")
        content_parts.append("  </TabItem>")
    
    content_parts.append("</Tabs>")
    content_parts.append("")
    
    return '\n'.join(content_parts)


def generate_docs():
    """Main function to generate documentation."""
    # Import the sup CLI app
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
    
    try:
        from sup.main import app
    except ImportError as e:
        print(f"Error importing sup CLI: {e}")
        print("Make sure the sup package is installed with: pip install -e .")
        return
    
    # Create output directory for commands only
    docs_dir = Path(__file__).parent.parent / "docs-site" / "src" / "content" / "docs"
    commands_dir = docs_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract command information
    print("Extracting command information from sup CLI...")
    commands = extract_command_info(app)
    
    # Generate MDX files for each command
    for cmd_name, cmd_info in commands.items():
        output_file = commands_dir / f"{cmd_name}.mdx"
        mdx_content = generate_command_mdx(cmd_info)
        
        output_file.write_text(mdx_content)
        print(f"✓ Generated: {output_file.relative_to(Path.cwd())}")
    
    print(f"\n✅ Command documentation generation complete!")
    print(f"📁 Generated {len(commands)} command reference pages")
    print(f"\nTo view the docs locally:")
    print(f"  cd docs-site")
    print(f"  npm run dev")


if __name__ == "__main__":
    generate_docs()