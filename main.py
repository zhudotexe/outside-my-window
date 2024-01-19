import asyncio

from outside.app import OutsideApp

if __name__ == "__main__":
    app = OutsideApp()
    asyncio.run(app.main())
