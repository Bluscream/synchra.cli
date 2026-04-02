import asyncio
import argparse
import os
import signal
from uuid import UUID

from synchra_py import SynchraClient
from .observer import SynchraObserver
from .input_handler import AsyncInput
from .formatter import Formatter

async def main():
    parser = argparse.ArgumentParser(description="Synchra CLI Observer")
    parser.add_argument("target", nargs="*", help="Channel ID, platform/name, or platform name (e.g. 'tiktok/user' or 'tiktok user')")
    parser.add_argument("--target", dest="opt_target", help="Legacy target flag (UUID or platform/name)")
    parser.add_argument("--token", help="Synchra API Access Token (env: SYNCHRA_TOKEN)")
    parser.add_argument("--timeout", type=int, help="Exit after X seconds (optional)")
    args = parser.parse_args()

    # Determine targeting info
    target_list = args.target if args.target else []
    if args.opt_target:
        # If legacy --target used, split if needed
        if "/" in args.opt_target and len(target_list) == 0:
            target_list = args.opt_target.split("/", 1)
        else:
            target_list.insert(0, args.opt_target)

    channel_id = None
    provider = None
    name = None

    if len(target_list) == 0:
        # Default behavior if nothing provided
        provider = "tiktok"
        name = "bleichiloveless"
    elif len(target_list) == 1:
        val = target_list[0]
        try:
            channel_id = UUID(val)
        except ValueError:
            if "/" in val:
                parts = val.split("/", 1)
                provider, name = parts[0], parts[1]
            else:
                provider = "tiktok"
                name = val
    else:
        provider = target_list[0]
        name = target_list[1]
    
    token = args.token or os.getenv("SYNCHRA_TOKEN")
    if not token:
        Formatter.error("Synchra Token is required! Use --token or set SYNCHRA_TOKEN environment variable.")
        return

    client = SynchraClient(access_token=token)
    observer = SynchraObserver(client)
    input_reader = AsyncInput()

    async def run_loop():
        # Setup channel and events
        await observer.setup(channel_id=channel_id, provider=provider, name=name)
        
        # Start non-blocking input reader task
        input_task = asyncio.create_task(input_reader.start())
        
        while True:
            # Check for input or wait for a small duration
            try:
                # message = await asyncio.wait_for(input_reader.get(), timeout=0.1)
                # Actually, we can just use an async loop with the queue
                user_input = await input_reader.queue.get()
                if user_input.lower() in ['/quit', '/exit', '/q']:
                    break
                
                await observer.send_broadcast(user_input)
                # print(f"Sent: {user_input}")
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.1)
            except Exception as e:
                # Formatter.error(f"Error: {e}")
                pass

    input_task = None
    try:
        if args.timeout:
            Formatter.info(f"Running with {args.timeout}s timeout...")
            try:
                # Setup and run loop with timeout
                await asyncio.wait_for(run_loop(), timeout=args.timeout)
            except asyncio.TimeoutError:
                Formatter.info("Timeout reached. Exiting...")
        else:
            await run_loop()

    except KeyboardInterrupt:
        Formatter.info("Exiting...")
    except Exception as e:
        Formatter.error(f"Fatal error: {e}")
    finally:
        # 1. Signal input reader to stop (daemon thread will die on process exit anyway)
        input_reader.stop()
        
        # 2. Close client
        await client.close()
        Formatter.info("Connections closed.")
        
        # 3. Final task cleanup to avoid 'NoneType' errors on loop close
        try:
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            pass

def entry_point():
    """Entry point for the CLI script defined in pyproject.toml."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    entry_point()
