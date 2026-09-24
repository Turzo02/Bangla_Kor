"""One-shot import test for Bangla Kor modules.

Run:  python test_imports.py
"""
import sys
import traceback

MODULES = [
    # root
    "config",
    "state",
    # platform_win
    "platform_win",
    "platform_win.api",
    "platform_win.hotkey",
    "platform_win.input",
    "platform_win.startup",
    "platform_win.single_instance",
    # core
    "core",
    "core.protect",
    "core.analyzer",
    "core.model",
    # ui
    "ui",
    "ui.toast",
    "ui.window",
    "ui.tray",
]


def main():
    print("=" * 60)
    print("Bangla Kor — Module Import Test")
    print("=" * 60)
    print()

    passed = []
    failed = []

    for name in MODULES:
        try:
            __import__(name)
            passed.append(name)
            print(f"  [ OK ]  {name}")
        except Exception as e:
            failed.append((name, e))
            print(f"  [FAIL]  {name}")
            print(f"          → {type(e).__name__}: {e}")

    print()
    print("=" * 60)
    print(f"Result: {len(passed)} passed, {len(failed)} failed")
    print("=" * 60)

    if failed:
        print()
        print("Failed modules — full traceback:")
        print("-" * 60)
        for name, err in failed:
            print(f"\n### {name}")
            traceback.print_exception(type(err), err, err.__traceback__)
        sys.exit(1)

    print()
    print("All modules imported successfully.")
    print("Next step:  python main.py")


if __name__ == "__main__":
    main()