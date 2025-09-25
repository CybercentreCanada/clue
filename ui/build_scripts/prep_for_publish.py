import json
import shutil
from pathlib import Path

print("Step 1: Copy Files")

ui_path = Path(__file__).parent.parent
lib_path = ui_path / "src" / "lib"

if not (ui_path / "dist" / ".npmrc").exists():
    print("\tCopying .npmrc")
    shutil.copy(ui_path / ".npmrc", ui_path / "dist" / ".npmrc")

if not (ui_path / "dist" / "index.css").exists():
    print("\tCopying index.css")
    shutil.copy(ui_path / "src" / "index.css", ui_path / "dist" / "index.css")

if not (ui_path / "dist" / "package.json").exists():
    print("\tCopying package.json")
    shutil.copy(ui_path / "package.json", ui_path / "dist" / "package.json")

if not (ui_path / "dist" / "public").exists():
    print("\tRecursively copying public path")
    shutil.copytree(ui_path / "public", ui_path / "dist" / "public")

print("Step 2: Prepare package.json")

package_json = json.loads((ui_path / "dist" / "package.json").read_text())

if "devDependencies" in package_json:
    print("\tRemoving devDependencies key")
    del package_json["devDependencies"]

if "lint" in package_json:
    print("\tRemoving lint-staged key")
    del package_json["lint-staged"]

if "scripts" in package_json:
    print("\tRemoving scripts key")
    del package_json["scripts"]

if "pnpm" in package_json:
    print("\tRemoving pnpm key")
    del package_json["pnpm"]

exports: list[Path] = []
for path in lib_path.rglob("**"):
    if path == lib_path:
        continue

    exports.append(path.relative_to(lib_path))

    if (
        index := next(
            (
                path / _index
                for _index in ["index.ts", "index.tsx"]
                if (path / _index).exists()
            ),
            None,
        )
    ) is not None:
        exports.append(index)


print(f"\t Writing {len(exports)} entries to exports")

package_json["exports"] = {
    ".": "./main.js",
    "./index.css": "./index.css",
    "./en/*.json": "./en/*.json",
    "./fr/*.json": "./fr/*.json",
}
for path in exports:
    if "." in path.name:
        package_json["exports"][f"./{path.parent.relative_to(lib_path)}"] = (
            f"./{path.parent.relative_to(lib_path)}/index.js"
        )
    elif str(path).startswith("locales"):
        package_json["exports"][f"./{path}/*.json"] = f"./{path}/*.json"
    elif "markdown" in str(path):
        package_json["exports"][f"./{path}/*.md"] = f"./{path}/*.md.js"
    elif str(path).startswith("utils"):
        package_json["exports"][f"./{path}/*"] = f"./{path}/*.js"
        package_json["exports"][f"./{path}/*.json"] = f"./{path}/*.json"
    else:
        package_json["exports"][f"./{path}/*"] = f"./{path}/*.js"

(ui_path / "dist" / "package.json").write_text(json.dumps(package_json, indent=2))

print("-" * 80)
