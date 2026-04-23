"""Bot launcher — istalgan papkadan ishga tushirish mumkin."""
import sys
import os

# Loyiha papkasini aniqlash
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
from bot.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot to'xtatildi")
    except Exception as e:
        print(f"❌ Xato: {e}")
        sys.exit(1)
