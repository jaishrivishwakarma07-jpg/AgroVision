"""
==========================================================
AgroVision
AI-Powered Smart Agriculture Management System
==========================================================
Author  : Jai Shri Vishwakarma
Version : 1.0
==========================================================
"""

from colorama import init, Fore
from modules.menu import main_menu

# Initialize Colorama
init(autoreset=True)


# ==========================================
# Welcome Screen
# ==========================================

def welcome_screen():
    
    """Display Welcome Screen"""

    print(Fore.GREEN + "=" * 60)
    print(Fore.CYAN + "                 AGROVISION")
    print(Fore.GREEN + "=" * 60)
    print(Fore.YELLOW + "    AI-Powered Smart Agriculture Management System")
    print(Fore.GREEN + "=" * 60)
    print(Fore.GREEN + "         🌱 Welcome to AgroVision 🌱")
    print(Fore.GREEN + "=" * 60)


# ==========================================
# Exit Program
# ==========================================

def exit_program():
    
    """Display Exit Message"""

    print(Fore.GREEN + "\n============================================")
    print(Fore.CYAN + "Thank you for using AgroVision!")
    print(Fore.YELLOW + "Empowering Smart Farming with AI 🌱")
    print(Fore.GREEN + "============================================")


# ==========================================
# Main Function
# ==========================================

def main():
    
    """Main Program"""

    welcome_screen()

    try:
        main_menu()
        
    except KeyboardInterrupt:
        print(Fore.RED + "\n\nProgram Interrupted by User!")

    exit_program()


# ==========================================
# Program Starts Here
# ==========================================

if __name__ == "__main__":
    main()