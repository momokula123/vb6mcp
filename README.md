# VB6 MCP Server

Visual Basic 6.0 Model Context Protocol Server for AI coding assistants (SOLO / Trae IDE).

## Features

- 13 VB6 development tools via MCP protocol
- Create, compile, edit VB6 projects
- Add forms, modules, classes
- Open VB6 IDE
- Run and stop VB6 projects
- Auto-detect VB6 installation and stdole2.tlb
- **v1.0.4**: Reliable compilation error reporting (exit code, MZ header validation, error parsing)

## Quick Start

### 1. Install VB6

Install Visual Basic 6.0 or VB6Mini to the default path:
```
C:\Program Files (x86)\VB6Mini\bin\VB6.EXE
```

### 2. Configure MCP

Add to your SOLO / Trae IDE MCP settings:

```json
{
  "mcpServers": {
    "vb6": {
      "command": "path/to/vb6mcp-v1.0.4.exe"
    }
  }
}
```

Or run from source with Python:

```json
{
  "mcpServers": {
    "vb6": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

### 3. Use

Ask your AI assistant to create VB6 projects, compile code, etc.

## Available Tools

| Tool | Description |
|------|-------------|
| `vb6_set_path` | Set/get VB6.EXE path |
| `vb6_compile` | Compile .vbp to EXE |
| `vb6_create_project` | Create new VB6 project |
| `vb6_write_code` | Write VB6 source code |
| `vb6_read_code` | Read VB6 source code |
| `vb6_add_module` | Add .bas module |
| `vb6_add_form` | Add .frm form |
| `vb6_add_class` | Add .cls class |
| `vb6_open_ide` | Open VB6 IDE |
| `vb6_run` | Run VB6 project |
| `vb6_stop` | Stop running VB6 |
| `vb6_project_info` | Get project info |
| `vb6_list_projects` | List .vbp files |

## Changelog

### v1.0.4
- Fixed `vb6_compile` returning false positive on compilation failure
- Added process exit code capture
- Added EXE file validation (size check + MZ header)
- Added compile error parsing from `/out` output file
- Process cleanup on timeout

### v1.0.3
- Added `vb6_write_code` for writing VB6 source files
- Added `vb6_read_code` for reading VB6 source files

### v1.0.2
- Added `vb6_open_ide`, `vb6_run`, `vb6_stop`

### v1.0.1
- Added `vb6_add_module`, `vb6_add_form`, `vb6_add_class`

### v1.0.0
- Initial release with core tools

## Requirements

- Windows
- Visual Basic 6.0 (or VB6Mini)
- No Python required for EXE version

## License

MIT
