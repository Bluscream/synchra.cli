from datetime import datetime

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
    def chat(cls, provider: str, user: str, message: str):
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
        
        print(f"[{cls.BLUE}{cls.get_timestamp()}{cls.RESET}] "
              f"{provider_color}{p_name.upper():<7}{cls.RESET} | "
              f"{cls.BOLD}{user}{cls.RESET}: {message}")

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
    def error(cls, text: str):
        print(f"[{cls.RED}{cls.get_timestamp()}{cls.RESET}] "
              f"{cls.RED}{cls.BOLD}ERROR{cls.RESET}   | {text}")
