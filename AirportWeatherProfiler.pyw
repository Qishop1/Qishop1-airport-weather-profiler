import sys

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--wxprofiler-cli":
    from wxprofiler.cli import main as cli_main
    cli_main(sys.argv[2:])
else:
    from wxprofiler.gui import main
    main()
