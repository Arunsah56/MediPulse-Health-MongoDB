"""
MediPulse Health - Hospital Management & Clinical Analytics System
CSE494: Intelligent NoSQL Databases - Project Driver
"""

import sys
from db_setup import initialize_database
from crud_ops import run_crud_tests
from aggregations import run_analytics_pipelines

def show_menu():
    print("""
======================================================
     MEDIPULSE HEALTH - MONGODB NOSQL SYSTEM
======================================================
1. Initialize Database & Apply $jsonSchema Validation
2. Execute CRUD Operations & Schema Integrity Check
3. Run Real-Time Analytical Aggregation Pipelines
4. Run Full Project Demonstration (All 1-3 sequentially)
5. Exit
======================================================
""")

def main():
    while True:
        show_menu()
        choice = input("Select an option (1-5): ").strip()
        
        if choice == "1":
            print("\n[Executing Task 1: Database Setup]")
            initialize_database()
        elif choice == "2":
            print("\n[Executing Task 2: CRUD Operations]")
            run_crud_tests()
        elif choice == "3":
            print("\n[Executing Task 3: Aggregation Pipelines]")
            run_analytics_pipelines()
        elif choice == "4":
            print("\n--- STEP 1: INITIALIZING DATABASE ---")
            initialize_database()
            print("\n--- STEP 2: RUNNING CRUD & VALIDATION ---")
            run_crud_tests()
            print("\n--- STEP 3: RUNNING ANALYTICS PIPELINES ---")
            run_analytics_pipelines()
            print("\n>>> Full project execution completed successfully!")
        elif choice == "5":
            print("\nExiting MediPulse System. Goodbye!")
            sys.exit(0)
        else:
            print("\n[!] Invalid selection. Please enter a number between 1 and 5.")

if __name__ == "__main__":
    main()