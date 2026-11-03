"""PyInstaller entry point."""
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        from backend.cli import main as cli_main
        raise SystemExit(cli_main(sys.argv[2:]))
    else:
        from backend.service import main
        main()
