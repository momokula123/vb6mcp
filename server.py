"""
VB6 MCP Server v1.0.4 - Compatible with SOLO / Trae IDE MCP client
Uses line-based JSON over stdio (MCP stdio transport standard)
"""
import sys
import os
import json
import subprocess
import re
import uuid
import time

VERSION = "1.0.4"
DEFAULT_VB6_PATH = r"C:\Program Files (x86)\VB6Mini\bin\VB6.EXE"

vb6_path = DEFAULT_VB6_PATH
running_processes = {}


def log(msg):
    sys.stderr.write(f"[vb6mcp] {msg}\n")
    sys.stderr.flush()


def find_vb6():
    global vb6_path
    if os.path.isfile(vb6_path):
        return vb6_path
    for p in [
        DEFAULT_VB6_PATH,
        r"C:\Program Files\Microsoft Visual Studio\VB98\VB6.EXE",
        r"C:\Program Files (x86)\Microsoft Visual Studio\VB98\VB6.EXE",
    ]:
        if os.path.isfile(p):
            vb6_path = p
            return p
    return None


def find_stdole2():
    exe_dir = os.path.dirname(vb6_path) if os.path.isfile(vb6_path) else ""
    search_paths = [
        os.path.join(exe_dir, "stdole2.tlb") if exe_dir else "",
        r"C:\Windows\SysWOW64\stdole2.tlb",
        r"C:\Windows\System32\stdole2.tlb",
    ]
    for p in search_paths:
        if p and os.path.isfile(p):
            return p
    return None


def run_vb6(args, timeout=120):
    exe = find_vb6()
    if not exe:
        return None, "VB6.EXE not found"
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.Popen(
            [exe] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=flags,
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc, None, stdout, stderr
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        return None, f"VB6 timed out after {timeout}s", b"", b""
    except Exception as e:
        return None, str(e), b"", b""


def validate_exe(filepath):
    if not os.path.isfile(filepath):
        return False, "File does not exist"
    size = os.path.getsize(filepath)
    if size < 1024:
        return False, f"File too small ({size} bytes), not a valid EXE"
    try:
        with open(filepath, "rb") as f:
            header = f.read(2)
        if header != b"MZ":
            return False, "Not a valid PE/EXE file (missing MZ header)"
    except Exception as e:
        return False, f"Cannot read file: {e}"
    return True, None


def parse_compile_output(out_file):
    errors = []
    try:
        with open(out_file, "r", encoding="gbk", errors="replace") as f:
            content = f.read()
    except Exception:
        return None
    for pattern in [
        r"编译错误.*?,\s*行\s*(\d+)\s*:\s*(.+)",
        r"compile error.*?line\s*(\d+)\s*:\s*(.+)",
        r"权限被拒绝",
        r"permission denied",
        r"编译失败",
        r"compile failed",
    ]:
        for m in re.finditer(pattern, content, re.IGNORECASE):
            errors.append(m.group(0) if m.lastindex == 0 else f"Line {m.group(1)}: {m.group(2)}")
    return errors if errors else [content.strip()[:500]] if content.strip() else None


def parse_vbp(filepath):
    info = {"file": filepath, "modules": [], "forms": [], "classes": [], "references": [], "properties": {}}
    if not os.path.isfile(filepath):
        return info, f"File not found: {filepath}"
    try:
        with open(filepath, "r", encoding="gbk", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return info, str(e)
    for line in content.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key == "Module":
            m = re.match(r"Module\s*=\s*(\S+)\s*;\s*(.+)", line)
            if m:
                info["modules"].append({"name": m.group(2), "file": m.group(1)})
            else:
                m2 = re.match(r"Module\s*=\s*(.+)", line)
                if m2:
                    info["modules"].append({"name": "", "file": m2.group(1).strip()})
        elif key == "Form":
            m = re.match(r"Form\s*=\s*(.+)", line)
            if m:
                info["forms"].append(m.group(1).strip())
        elif key == "Class":
            m = re.match(r"Class\s*=\s*(\S+)\s*;\s*(.+)", line)
            if m:
                info["classes"].append({"name": m.group(2), "file": m.group(1)})
        elif key == "Reference":
            info["references"].append(line.split("=", 1)[1].strip())
        else:
            info["properties"][key] = line.split("=", 1)[1].strip()
    return info, None


def create_project_impl(project_dir, project_name, project_type="Standard EXE"):
    os.makedirs(project_dir, exist_ok=True)
    vbp_path = os.path.join(project_dir, f"{project_name}.vbp")
    frm_path = os.path.join(project_dir, "Form1.frm")
    bas_path = os.path.join(project_dir, "Module1.bas")

    frm = (
        'VERSION 5.00\r\n'
        'Begin VB.Form Form1\r\n'
        f'   Caption         =   "{project_name}"\r\n'
        '   ClientHeight    =   3600\r\n'
        '   ClientLeft      =   60\r\n'
        '   ClientTop       =   450\r\n'
        '   ClientWidth     =   4800\r\n'
        '   LinkTopic       =   "Form1"\r\n'
        '   ScaleHeight     =   3600\r\n'
        '   ScaleMode       =   1\r\n'
        '   ScaleWidth      =   4800\r\n'
        '   StartUpPosition =   2\r\n'
        '   Begin VB.CommandButton Command1\r\n'
        '      Caption         =   "OK"\r\n'
        '      Height          =   495\r\n'
        '      Left            =   1800\r\n'
        '      TabIndex        =   0\r\n'
        '      Top             =   2640\r\n'
        '      Width           =   1215\r\n'
        '   End\r\n'
        '   Begin VB.Label Label1\r\n'
        '      Alignment       =   2\r\n'
        '      Caption         =   "Hello VB6!"\r\n'
        '      Height          =   375\r\n'
        '      Left            =   120\r\n'
        '      TabIndex        =   1\r\n'
        '      Top             =   1200\r\n'
        '      Width           =   4575\r\n'
        '   End\r\n'
        'End\r\n'
        'Attribute VB_Name = "Form1"\r\n'
        'Attribute VB_GlobalNameSpace = False\r\n'
        'Attribute VB_Creatable = False\r\n'
        'Attribute VB_PredeclaredId = True\r\n'
        'Attribute VB_Exposed = False\r\n'
        'Option Explicit\r\n'
        '\r\n'
        'Private Sub Command1_Click()\r\n'
        f'    MsgBox "Hello from VB6!", vbInformation, "{project_name}"\r\n'
        'End Sub\r\n'
    )

    bas = (
        'Attribute VB_Name = "Module1"\r\n'
        'Option Explicit\r\n'
        '\r\n'
        'Public Sub Main()\r\n'
        '    Form1.Show\r\n'
        'End Sub\r\n'
    )

    stdole_path = find_stdole2()
    ref_line = f"Reference=\\*\\G{{00020430-0000-0000-C000-000000000046}}#2.0#0#{stdole_path}#OLE Automation\r\n" if stdole_path else ""

    vbp = (
        "Type=Exe\r\n"
        + ref_line +
        "Module=Module1; Module1.bas\r\n"
        "Form=Form1.frm\r\n"
        'Startup="Module1"\r\n'
        'HelpFile=""\r\n'
        f'Title="{project_name}"\r\n'
        f'ExeName32="{project_name}.exe"\r\n'
        'Command32=""\r\n'
        f'Name="{project_name}"\r\n'
        'HelpContextID="0"\r\n'
        'CompatibleMode="0"\r\n'
        "MajorVer=1\r\nMinorVer=0\r\nRevisionVer=0\r\n"
        "AutoIncrementVer=0\r\nServerSupportFiles=0\r\n"
        "CompilationType=0\r\nOptimizationType=0\r\n"
        "FavorPentiumPro(tm)=0\r\nCodeViewDebugInfo=0\r\n"
        "NoAliasing=0\r\nBoundsCheck=0\r\nOverflowCheck=0\r\n"
        "FlPointCheck=0\r\nFDIVCheck=0\r\nUnroundedFP=0\r\n"
        "StartMode=0\r\nUnattended=0\r\nRetained=0\r\n"
        "ThreadPerObject=0\r\nMaxNumberOfThreads=1\r\n"
    )

    try:
        with open(frm_path, "w", encoding="gbk") as f:
            f.write(frm)
        with open(bas_path, "w", encoding="gbk") as f:
            f.write(bas)
        with open(vbp_path, "w", encoding="gbk") as f:
            f.write(vbp)
        return {"success": True, "project_file": vbp_path, "form_file": frm_path, "module_file": bas_path, "project_type": project_type}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_module_impl(project_dir, module_name, project_file=None):
    bas_path = os.path.join(project_dir, f"{module_name}.bas")
    try:
        with open(bas_path, "w", encoding="gbk") as f:
            f.write(f'Attribute VB_Name = "{module_name}"\r\nOption Explicit\r\n\r\n')
    except Exception as e:
        return {"success": False, "error": str(e)}
    if project_file and os.path.isfile(project_file):
        try:
            with open(project_file, "r", encoding="gbk", errors="replace") as f:
                vbp = f.read()
            marker = f"Module={module_name}; {module_name}.bas"
            if marker not in vbp:
                lines = vbp.rstrip().split("\n")
                idx = next((i for i, l in enumerate(lines) if l.strip().startswith("Form=")), len(lines))
                lines.insert(idx, marker)
                with open(project_file, "w", encoding="gbk") as f:
                    f.write("\n".join(lines) + "\n")
        except Exception as e:
            return {"success": True, "module_file": bas_path, "warning": f".vbp update failed: {e}"}
    return {"success": True, "module_file": bas_path, "module_name": module_name}


def add_form_impl(project_dir, form_name, project_file=None):
    frm_path = os.path.join(project_dir, f"{form_name}.frm")
    content = (
        'VERSION 5.00\r\n'
        f'Begin VB.Form {form_name}\r\n'
        f'   Caption         =   "{form_name}"\r\n'
        '   ClientHeight    =   3600\r\n'
        '   ClientLeft      =   60\r\n'
        '   ClientTop       =   450\r\n'
        '   ClientWidth     =   4800\r\n'
        f'   LinkTopic       =   "{form_name}"\r\n'
        '   ScaleHeight     =   3600\r\n'
        '   ScaleMode       =   1\r\n'
        '   ScaleWidth      =   4800\r\n'
        '   StartUpPosition =   2\r\n'
        'End\r\n'
        f'Attribute VB_Name = "{form_name}"\r\n'
        'Attribute VB_GlobalNameSpace = False\r\n'
        'Attribute VB_Creatable = False\r\n'
        'Attribute VB_PredeclaredId = True\r\n'
        'Attribute VB_Exposed = False\r\n'
        'Option Explicit\r\n'
    )
    try:
        with open(frm_path, "w", encoding="gbk") as f:
            f.write(content)
    except Exception as e:
        return {"success": False, "error": str(e)}
    if project_file and os.path.isfile(project_file):
        try:
            with open(project_file, "r", encoding="gbk", errors="replace") as f:
                vbp = f.read()
            marker = f"Form={form_name}.frm"
            if marker not in vbp:
                lines = vbp.rstrip().split("\n")
                idx = next((i for i, l in enumerate(lines) if l.strip().startswith("Class=")), len(lines))
                lines.insert(idx, marker)
                with open(project_file, "w", encoding="gbk") as f:
                    f.write("\n".join(lines) + "\n")
        except Exception as e:
            return {"success": True, "form_file": frm_path, "warning": f".vbp update failed: {e}"}
    return {"success": True, "form_file": frm_path, "form_name": form_name}


def add_class_impl(project_dir, class_name, project_file=None):
    cls_path = os.path.join(project_dir, f"{class_name}.cls")
    content = (
        'VERSION 1.0 CLASS\r\nBEGIN\r\n'
        '  MultiUse = -1\r\n  Persistable = 0\r\n'
        '  DataBindingBehavior = 0\r\n  DataSourceBehavior = 0\r\n'
        '  MTSTransactionMode = 0\r\nEND\r\n'
        f'Attribute VB_Name = "{class_name}"\r\n'
        'Attribute VB_GlobalNameSpace = False\r\n'
        'Attribute VB_Creatable = False\r\n'
        'Attribute VB_PredeclaredId = False\r\n'
        'Attribute VB_Exposed = False\r\n'
        'Option Explicit\r\n'
    )
    try:
        with open(cls_path, "w", encoding="gbk") as f:
            f.write(content)
    except Exception as e:
        return {"success": False, "error": str(e)}
    if project_file and os.path.isfile(project_file):
        try:
            with open(project_file, "r", encoding="gbk", errors="replace") as f:
                vbp = f.read()
            marker = f"Class={class_name}; {class_name}.cls ; {class_name}"
            if marker not in vbp:
                with open(project_file, "a", encoding="gbk") as f:
                    f.write(f"\n{marker}\n")
        except Exception as e:
            return {"success": True, "class_file": cls_path, "warning": f".vbp update failed: {e}"}
    return {"success": True, "class_file": cls_path, "class_name": class_name}


TOOLS = [
    {"name": "vb6_set_path", "description": "Set or get the VB6.EXE path.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string", "description": "Full path to VB6.EXE"}}}},
    {"name": "vb6_compile", "description": "Compile a VB6 project (.vbp) to EXE.",
     "inputSchema": {"type": "object", "properties": {
         "project_file": {"type": "string", "description": "Path to .vbp file"},
         "output_file": {"type": "string", "description": "Optional output EXE path"},
         "timeout": {"type": "integer", "description": "Timeout seconds (default 120)"},
     }, "required": ["project_file"]}},
    {"name": "vb6_create_project", "description": "Create a new VB6 project with form and module.",
     "inputSchema": {"type": "object", "properties": {
         "project_dir": {"type": "string", "description": "Directory to create project in"},
         "project_name": {"type": "string", "description": "Project name"},
         "project_type": {"type": "string", "enum": ["Standard EXE", "ActiveX EXE", "ActiveX DLL", "ActiveX Control"], "default": "Standard EXE"},
     }, "required": ["project_dir", "project_name"]}},
    {"name": "vb6_write_code", "description": "Write VB6 source code to a file (.bas, .cls, .frm).",
     "inputSchema": {"type": "object", "properties": {
         "file_path": {"type": "string"}, "code": {"type": "string"},
     }, "required": ["file_path", "code"]}},
    {"name": "vb6_read_code", "description": "Read VB6 source code from a file.",
     "inputSchema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}},
    {"name": "vb6_add_module", "description": "Add a .bas module to a VB6 project.",
     "inputSchema": {"type": "object", "properties": {
         "project_dir": {"type": "string"}, "module_name": {"type": "string"}, "project_file": {"type": "string"},
     }, "required": ["project_dir", "module_name"]}},
    {"name": "vb6_add_form", "description": "Add a .frm form to a VB6 project.",
     "inputSchema": {"type": "object", "properties": {
         "project_dir": {"type": "string"}, "form_name": {"type": "string"}, "project_file": {"type": "string"},
     }, "required": ["project_dir", "form_name"]}},
    {"name": "vb6_add_class", "description": "Add a .cls class module to a VB6 project.",
     "inputSchema": {"type": "object", "properties": {
         "project_dir": {"type": "string"}, "class_name": {"type": "string"}, "project_file": {"type": "string"},
     }, "required": ["project_dir", "class_name"]}},
    {"name": "vb6_open_ide", "description": "Open VB6 IDE with a project file.",
     "inputSchema": {"type": "object", "properties": {"project_file": {"type": "string"}}, "required": ["project_file"]}},
    {"name": "vb6_run", "description": "Run a VB6 project without compiling. Returns session_id.",
     "inputSchema": {"type": "object", "properties": {"project_file": {"type": "string"}}, "required": ["project_file"]}},
    {"name": "vb6_stop", "description": "Stop a running VB6 process by session_id, or all if empty.",
     "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}}}},
    {"name": "vb6_project_info", "description": "Get info about a VB6 project (.vbp).",
     "inputSchema": {"type": "object", "properties": {"project_file": {"type": "string"}}, "required": ["project_file"]}},
    {"name": "vb6_list_projects", "description": "List .vbp files in a directory.",
     "inputSchema": {"type": "object", "properties": {
         "directory": {"type": "string"}, "recursive": {"type": "boolean", "default": False},
     }, "required": ["directory"]}},
]

SERVER_INFO = {"name": "vb6mcp", "version": VERSION}
CAPABILITIES = {"tools": {}}


def handle_tool(name, args):
    if name == "vb6_set_path":
        global vb6_path
        if args.get("path"):
            if os.path.isfile(args["path"]):
                vb6_path = args["path"]
                return {"success": True, "vb6_path": vb6_path}
            return {"success": False, "error": f"Not found: {args['path']}"}
        return {"vb6_path": vb6_path, "exists": os.path.isfile(vb6_path)}

    elif name == "vb6_compile":
        pf = args["project_file"]
        if not os.path.isfile(pf):
            return {"success": False, "error": f"Not found: {pf}"}
        a = ["/make", pf]
        out_file = args.get("output_file")
        if out_file:
            a.extend(["/out", out_file])
        proc, err, stdout, stderr = run_vb6(a, timeout=args.get("timeout", 120))
        if err:
            return {"success": False, "error": err}
        exit_code = proc.returncode if proc else -1
        proj_dir = os.path.dirname(pf)
        proj_name = os.path.splitext(os.path.basename(pf))[0]
        exe = out_file or os.path.join(proj_dir, proj_name + ".exe")
        is_valid, val_err = validate_exe(exe)
        if is_valid:
            return {"success": True, "exe_file": exe, "exe_exists": True, "exit_code": exit_code, "size": os.path.getsize(exe)}
        compile_errors = []
        if out_file and os.path.isfile(out_file):
            parsed = parse_compile_output(out_file)
            if parsed:
                compile_errors = parsed
        if stderr:
            try:
                compile_errors.append(stderr.decode("gbk", errors="replace").strip()[:300])
            except Exception:
                pass
        if stdout:
            try:
                compile_errors.append(stdout.decode("gbk", errors="replace").strip()[:300])
            except Exception:
                pass
        error_msg = val_err or "Compilation failed"
        if compile_errors:
            error_msg += " | " + "; ".join(compile_errors)
        return {"success": False, "error": error_msg, "exit_code": exit_code, "exe_file": exe}

    elif name == "vb6_create_project":
        return create_project_impl(args["project_dir"], args["project_name"], args.get("project_type", "Standard EXE"))

    elif name == "vb6_write_code":
        try:
            os.makedirs(os.path.dirname(args["file_path"]) or ".", exist_ok=True)
            with open(args["file_path"], "w", encoding="gbk") as f:
                f.write(args["code"])
            return {"success": True, "file": args["file_path"], "size": len(args["code"])}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif name == "vb6_read_code":
        fp = args["file_path"]
        if not os.path.isfile(fp):
            return {"success": False, "error": f"Not found: {fp}"}
        try:
            with open(fp, "r", encoding="gbk", errors="replace") as f:
                c = f.read()
            return {"success": True, "file": fp, "content": c, "size": len(c)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif name == "vb6_add_module":
        return add_module_impl(args["project_dir"], args["module_name"], args.get("project_file"))

    elif name == "vb6_add_form":
        return add_form_impl(args["project_dir"], args["form_name"], args.get("project_file"))

    elif name == "vb6_add_class":
        return add_class_impl(args["project_dir"], args["class_name"], args.get("project_file"))

    elif name == "vb6_open_ide":
        pf = args["project_file"]
        if not os.path.isfile(pf):
            return {"success": False, "error": f"Not found: {pf}"}
        exe = find_vb6()
        if not exe:
            return {"success": False, "error": "VB6.EXE not found"}
        try:
            subprocess.Popen([exe, pf], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
            return {"success": True, "message": f"VB6 IDE opened: {pf}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif name == "vb6_run":
        pf = args["project_file"]
        if not os.path.isfile(pf):
            return {"success": False, "error": f"Not found: {pf}"}
        exe = find_vb6()
        if not exe:
            return {"success": False, "error": "VB6.EXE not found"}
        try:
            proc = subprocess.Popen([exe, "/run", pf], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
            sid = str(uuid.uuid4())[:8]
            running_processes[sid] = {"pid": proc.pid, "project": pf, "start_time": time.time()}
            return {"success": True, "session_id": sid, "pid": proc.pid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif name == "vb6_stop":
        sid = args.get("session_id", "")
        if sid:
            if sid in running_processes:
                pid = running_processes[sid]["pid"]
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                del running_processes[sid]
                return {"success": True, "message": f"Killed {pid}"}
            return {"success": False, "error": f"Session {sid} not found"}
        killed = []
        for s, info in list(running_processes.items()):
            subprocess.run(["taskkill", "/F", "/PID", str(info["pid"])], capture_output=True)
            killed.append(s)
        for s in killed:
            del running_processes[s]
        return {"success": True, "killed": killed}

    elif name == "vb6_project_info":
        info, err = parse_vbp(args["project_file"])
        if err:
            return {"success": False, "error": err}
        info["success"] = True
        return info

    elif name == "vb6_list_projects":
        d = args["directory"]
        if not os.path.isdir(d):
            return {"success": False, "error": f"Not found: {d}"}
        projs = []
        if args.get("recursive"):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".vbp"):
                        projs.append(os.path.join(root, f))
        else:
            for f in os.listdir(d):
                if f.lower().endswith(".vbp"):
                    projs.append(os.path.join(d, f))
        return {"success": True, "projects": projs, "count": len(projs)}

    return {"error": f"Unknown tool: {name}"}


def send(obj):
    line = json.dumps(obj, ensure_ascii=False)
    sys.stdout.buffer.write(line.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def recv():
    raw = sys.stdin.buffer.readline()
    if not raw:
        return None
    line = raw.decode("utf-8", errors="replace").strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def main():
    find_vb6()
    log(f"v{VERSION} started, vb6={vb6_path}")

    while True:
        msg = recv()
        if msg is None:
            break

        method = msg.get("method", "")
        req_id = msg.get("id")
        params = msg.get("params", {})

        if method == "notifications/initialized":
            continue

        if method == "initialize":
            send({"jsonrpc": "2.0", "id": req_id, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": CAPABILITIES,
                "serverInfo": SERVER_INFO,
            }})

        elif method == "ping":
            send({"jsonrpc": "2.0", "id": req_id, "result": {}})

        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                result = handle_tool(tool_name, arguments)
                is_err = not result.get("success", True) if isinstance(result, dict) else False
                send({"jsonrpc": "2.0", "id": req_id, "result": {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
                    "isError": is_err,
                }})
            except Exception as e:
                send({"jsonrpc": "2.0", "id": req_id, "result": {
                    "content": [{"type": "text", "text": json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)}],
                    "isError": True,
                }})

        elif method in ("resources/list", "prompts/list"):
            send({"jsonrpc": "2.0", "id": req_id, "result": {"resources": []} if "resources" in method else {"prompts": []}})

        elif req_id is not None:
            send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Not found: {method}"}})


if __name__ == "__main__":
    main()
