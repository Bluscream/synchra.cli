from datetime import datetime
from typing import Optional, Any
from synchra.models import AccessLevel

class Formatter:
    """Utilities for colored and formatted console output."""
    
    # ANSI Color Codes
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    @staticmethod
    def get_timestamp() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @classmethod
    def chat(cls, provider: str, user: str, message: str, access_level: Optional[Any] = None):
        # Normalize provider name
        p_name = str(provider).lower()
        
        # Color mapping by provider
        colors = {
            "tiktok": cls.CYAN,
            "twitch": cls.MAGENTA,
            "youtube": cls.RED,
            "synchra": cls.GREEN
        }
        provider_color = colors.get(p_name, cls.YELLOW)
        
        # Format Access Level
        al_str = ""
        if access_level is not None:
            try:
                # Try to get the enum name
                if isinstance(access_level, int):
                    al_name = AccessLevel(access_level).name
                elif hasattr(access_level, 'name'):
                    al_name = access_level.name
                else:
                    al_name = str(access_level)
                
                # Colors for different levels
                if al_name in ["OWNER", "GLOBAL_ADMIN", "ADMIN"]:
                    al_str = f"[{cls.RED}{al_name}{cls.RESET}] "
                elif al_name in ["MOD", "EDITOR"]:
                    al_str = f"[{cls.GREEN}{al_name}{cls.RESET}] "
                elif al_name in ["VIP", "SUB"]:
                    al_str = f"[{cls.MAGENTA}{al_name}{cls.RESET}] "
                else:
                    al_str = f"[{cls.BLUE}{al_name}{cls.RESET}] "
            except:
                al_str = f"[{cls.YELLOW}{access_level}{cls.RESET}] "

        print(f"[{cls.BLUE}{cls.get_timestamp()}{cls.RESET}] "
              f"{provider_color}{p_name.upper():<7}{cls.RESET} | "
              f"{al_str}{cls.BOLD}{user}{cls.RESET}: {message}")

    @classmethod
    def activity(cls, provider: str, type: str, message: str):
        print(f"[{cls.BLUE}{cls.get_timestamp()}{cls.RESET}] "
              f"{cls.YELLOW}{'EVENT':<7}{cls.RESET} | "
              f"{cls.GREEN}{message}{cls.RESET}")

    @classmethod
    def info(cls, text: str):
        print(f"[{cls.BLUE}{cls.get_timestamp()}{cls.RESET}] "
              f"{cls.BOLD}INFO{cls.RESET}    | {text}")

    @classmethod
    def profile(cls, title: str, details: dict):
        print(f"\n{cls.BOLD}{cls.CYAN}=== {title.upper()} ==={cls.RESET}")
        for k, v in details.items():
            key_str = f"{cls.YELLOW}{k.replace('_', ' ').title():<15}{cls.RESET}"
            print(f"{key_str}: {v}")
        print(f"{cls.CYAN}{'=' * (len(title) + 8)}{cls.RESET}\n")

    @classmethod
    def error(cls, text: str):
        print(f"[{cls.RED}{cls.get_timestamp()}{cls.RESET}] "
              f"{cls.RED}{cls.BOLD}ERROR{cls.RESET}   | {text}")
