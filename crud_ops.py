from pymongo.errors import WriteError
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["MediPulseHealth"]

def run_crud_tests():
    print("--- Running CRUD Operations & Schema Checks ---")

    # 1. CREATE: Insert valid patient
    patient_one = {
        "patient_id": "PAT-10001",
        "full_name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "gender": "Male",
        "dob": "1998-05-14",
        "contact": "+91-9876543210",
        "blood_group": "B+",
        "allergies": ["Penicillin", "Dust"]
    }
    
    try:
        res = db.patients.insert_one(patient_one)
        print(f"[Create] Added patient with ID: {res.inserted_id}")
    except WriteError as err:
        print(f"[Error] Failed to insert patient: {err}")

    # 1.1 Negative Test: Invalid patient to verify schema validator catches bad inputs
    bad_patient = {
        "patient_id": "PAT-99999",
        "full_name": "Test User",
        "email": "invalid_email_format",  # fails regex
        "gender": "Male",
        "contact": "9999999999"
        # omitted 'dob' intentionally
    }
    try:
        db.patients.insert_one(bad_patient)
        print("[Warning] Bad record was accepted unexpectedly!")
    except WriteError as err:
        print("[Schema Check Passed] MongoDB blocked invalid patient record:")
        print(f" -> Message: {err.details.get('errmsg')}")

    # 1.2 Insert initial appointment documents
    sample_appointments = [
        {
            "appointment_id": "APT-20001",
            "patient_id": "PAT-10001",
            "doctor_id": "DOC-501",
            "department": "Cardiology",
            "date": "2026-10-25",
            "status": "Scheduled",
            "billing": {
                "consultation_fee": 800,
                "medication_fee": 300,
                "total_amount": 1100,
                "payment_status": "Paid"
            },
            "prescriptions": [
                {"medicine_name": "Atorvastatin", "dosage_mg": 20, "duration_days": 30}
            ]
        },
        {
            "appointment_id": "APT-20002",
            "patient_id": "PAT-10001",
            "doctor_id": "DOC-502",
            "department": "General Medicine",
            "date": "2026-10-28",
            "status": "Scheduled",
            "billing": {
                "consultation_fee": 500,
                "medication_fee": 150,
                "total_amount": 650,
                "payment_status": "Pending"
            },
            "prescriptions": [
                {"medicine_name": "Paracetamol", "dosage_mg": 500, "duration_days": 5}
            ]
        }
    ]
    db.appointments.insert_many(sample_appointments)
    print(f"[Create] Inserted {len(sample_appointments)} sample appointments.")

    # 2. READ: Query appointments with criteria & projection
    print("\n--- Testing Read Query ---")
    query = {"department": "Cardiology", "billing.total_amount": {"$gte": 500}}
    projection = {"_id": 0, "appointment_id": 1, "department": 1, "billing.total_amount": 1, "status": 1}
    cardiology_cases = list(db.appointments.find(query, projection))
    print(f"Found Cardiology appointments (total >= 500): {cardiology_cases}")

    # 3. UPDATE: Atomic array append and numeric adjustments ($push, $inc, $set)
    print("\n--- Testing Atomic Update ---")
    extra_med = {"medicine_name": "Aspirin", "dosage_mg": 75, "duration_days": 15}
    update_result = db.appointments.update_one(
        {"appointment_id": "APT-20001"},
        {
            "$push": {"prescriptions": extra_med},
            "$inc": {"billing.medication_fee": 120, "billing.total_amount": 120},
            "$set": {"status": "Completed"}
        }
    )
    print(f"[Update] Modified count: {update_result.modified_count}")

    # Inspect the updated record
    record = db.appointments.find_one(
        {"appointment_id": "APT-20001"},
        {"_id": 0, "appointment_id": 1, "prescriptions": 1, "billing": 1, "status": 1}
    )
    print(f"Updated appointment details: {record}")

    # 4. DELETE: Cancel appointment by ID
    print("\n--- Testing Delete Query ---")
    del_result = db.appointments.delete_one({"appointment_id": "APT-20002"})
    print(f"[Delete] Removed appointment APT-20002. Deleted count: {del_result.deleted_count}")

if __name__ == "__main__":
    run_crud_tests()