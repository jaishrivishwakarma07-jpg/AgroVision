"""
==========================================================
AgroVision
Main Menu Module
==========================================================
"""

from colorama import Fore
from modules.login import login_user, register_user


def main_menu():

    while True:

        print(Fore.CYAN + "\n========== MAIN MENU ==========")
        
        print("1. Login")
        print("2. Register")
        print("3. About AgroVision")
        print("4. Exit")

        choice = input("\nEnter your choice: ")

        if choice == "1":
            login_user()

        elif choice == "2":
            register_user()

        elif choice == "3":
            
            print(Fore.GREEN + "\n========== ABOUT AGROVISION ==========")
            
            print("Project Name : AgroVision")
            print("Version      : 1.0")
            print("Technology   : Python")
            print("Database     : JSON")
            print("AI           : Rule-Based AI (Currently)")
            print("Purpose      : AI-Powered Smart Agriculture Management System")

        elif choice == "4":
            print(Fore.YELLOW + "\nThank you for using AgroVision!")
            break

        else:
            print(Fore.RED + "\nInvalid Choice!")