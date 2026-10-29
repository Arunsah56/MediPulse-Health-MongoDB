from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Local MongoDB connection setup

MONGO_URI = os.getenv("MONGO_URI")




DB_NAME = "MediPulseHealth"

def initialize_database():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    print(f"Connected to MongoDB instance at: {MONGO_URI}")

    # Schema rule for patients collection
    # Ensures basic contact details, proper ID formats, and standard fields
    patient_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["patient_id", "full_name", "email", "gender", "dob", "contact"],
            "properties": {
                "patient_id": {
                    "bsonType": "string",
                    "pattern": "^PAT-[0-9]{4,5}$",
                    "description": "Patient ID format PAT-XXXX"
                },
                "full_name": {
                    "bsonType": "string",
                    "minLength": 3
                },
                "email": {
                    "bsonType": "string",
                    "pattern": "^.+@.+$"
                },
                "gender": {
                    "enum": ["Male", "Female", "Other"]
                },
                "dob": {
                    "bsonType": "string",
                    "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
                },
                "contact": {
                    "bsonType": "string"
                },
                "blood_group": {
                    "enum": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
                },
                "allergies": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"}
                }
            }
        }
    }

    # Schema rule for clinical appointments
    # Embeds prescription items and billing object directly for single-document reads
    appointment_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["appointment_id", "patient_id", "doctor_id", "department", "date", "status", "billing"],
            "properties": {
                "appointment_id": {
                    "bsonType": "string",
                    "pattern": "^APT-[0-9]{4,5}$"
                },
                "patient_id": {"bsonType": "string"},
                "doctor_id": {"bsonType": "string"},
                "department": {
                    "enum": ["Cardiology", "Neurology", "Pediatrics", "Orthopedics", "General Medicine"]
                },
                "date": {
                    "bsonType": "string",
                    "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
                },
                "status": {
                    "enum": ["Scheduled", "Completed", "Cancelled"]
                },
                "billing": {
                    "bsonType": "object",
                    "required": ["consultation_fee", "medication_fee", "total_amount", "payment_status"],
                    "properties": {
                        "consultation_fee": {"bsonType": ["double", "int"], "minimum": 0},
                        "medication_fee": {"bsonType": ["double", "int"], "minimum": 0},
                        "total_amount": {"bsonType": ["double", "int"], "minimum": 0},
                        "payment_status": {"enum": ["Paid", "Pending", "Claimed"]}
                    }
                },
                "prescriptions": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["medicine_name", "dosage_mg", "duration_days"],
                        "properties": {
                            "medicine_name": {"bsonType": "string"},
                            "dosage_mg": {"bsonType": "int", "minimum": 1},
                            "duration_days": {"bsonType": "int", "minimum": 1}
                        }
                    }
                }
            }
        }
    }

    # Clean existing collections before recreating with fresh schema
    available_collections = db.list_collection_names()
    if "patients" in available_collections:
        db.patients.drop()
    if "appointments" in available_collections:
        db.appointments.drop()

    # Re-create collections with validators attached
    db.create_collection("patients", validator=patient_schema)
    print("Created 'patients' collection with validation schema.")

    db.create_collection("appointments", validator=appointment_schema)
    print("Created 'appointments' collection with validation schema.")

    print("Database setup complete.")

if __name__ == "__main__":
    initialize_database()