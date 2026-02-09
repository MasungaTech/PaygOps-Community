from os import getenv

def initialize_debugger(port):
    if getenv("DEBUGGER") == "true":
        import multiprocessing

        if multiprocessing.current_process().pid > 1:
            import debugpy

            try:
                debugpy.listen(('0.0.0.0', port))
                print("⏳ VS Code debugger can now be attached, press F5 in VS Code ⏳", flush=True)

                debugpy.wait_for_client()
                print("🎉 VS Code debugger attached, enjoy debugging 🎉", flush=True)
            except Exception as e:
                print(e)
