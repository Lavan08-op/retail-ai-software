"""Compatibility entrypoint; canonical implementation lives in app/."""

from app.start_storesense import StoreSenseLauncher, main

__all__ = ["StoreSenseLauncher", "main"]


if __name__ == "__main__":
    main()
