import sys
from isodrome import __version__

def main():
    """Main CLI entry point for isodrome and iso commands."""
    # Check if the user passed a version flag
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(f"isodrome version {__version__}")
    else:
        print(f"Isodrome CLI (v{__version__}) - Early Development")
        print("Use --version for version information.")

if __name__ == "__main__":
    main()
