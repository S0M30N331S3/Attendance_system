from add_data_to_database import add_employee, update_employee_face, remove_employee, add_multiple_employees

def main():
    while True:
        print("\n=== Employee Database Control Panel ===")
        print("1. Add a new employee")
        print("2. Update an employee's face")
        print("3. Remove an employee")
        print("4. Add multiple employees")
        print("5. Exit")

        choice = input("Please select an option (1-5): ")

        if choice == '1':
            name = input("Enter the employee's name: ")
            add_employee(name)

        elif choice == '2':
            employee_id = input("Enter the employee ID to update: ")
            update_employee_face(employee_id)

        elif choice == '3':
            employee_id = input("Enter the employee ID to remove: ")
            remove_employee(employee_id)

        elif choice == '4':
            names = input("Enter the names of employees separated by commas: ")
            names_list = [name.strip() for name in names.split(',')]
            add_multiple_employees(names_list)

        elif choice == '5':
            print("Exiting the control panel.")
            break

        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
