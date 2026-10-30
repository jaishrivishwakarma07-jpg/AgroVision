import json
import os
from colorama import Fore
from modules.dashboard import admin_dashboard

USER_FILE = "database/users.json"

# ==========================================
# Load Users
# ==========================================

def load_users():
    
    if not os.path.exists(USER_FILE):
        return[]
    
    with open(USER_FILE, "r") as file:
        try:
            return json.load(file)
        
        except:
            return[]
        
        
# ==========================================
# Save Users
# ==========================================

def save_users(users):
    
    with open(USER_FILE, "w") as file:
        json.dump(users, file, indent = 4)
        

# ==========================================
# Register User
# ==========================================

def register_user():
    
    print(Fore.CYAN + "\n========== USER REGISTRATION ==========\n")
    
    users = load_users()
    
    name = input("Enter Full Name : ")
    username = input("Enter Username : ")
    
    for user in users:
        if user["username"] == username:
            print(Fore.RED + "\nUsername already exists!\n")
            return
        
    password = input("Enter Password : ")
    mobile = input("Enter Mobile Number : ")
    village  = input("Enter Village : ")
    
    new_user = {
        "id": len(users) + 1,
        "name": name,
        "username": username,
        "password": password,
        "mobile": mobile,
        "village": village,
        "role": "farmer"                 
    }
    
    users.append(new_user)
    save_users(users)
    
    print(Fore.GREEN + "\nRegistration Successful!\n")
    

# ==========================================
# Login User
# ==========================================

def login_user():
    
    print(Fore.CYAN + "\n========== LOGIN ==========\n")
    
    users = load_users()
    
    username = input("Username : ")
    password = input("Password : ")
    
    for user in users:
        
        if user["username"] == username and  user["password"] == password:
           
           print(Fore.GREEN + "\nLogin Successful!\n")

           print(Fore.YELLOW + f"Welcome {user['name']}")
           print(Fore.YELLOW + f"Role : {user['role']}\n")

           if user["role"] == "admin":
               admin_dashboard()

           return user
    
    print(Fore.RED + "\nInvalid Username or Password!\n")
    return None
        
        