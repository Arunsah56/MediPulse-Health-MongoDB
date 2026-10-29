import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["MediPulseHealth"]

def run_analytics_pipelines():
    # -------------------------------------------------------------
    # 1. Pipeline: Department revenue and completed case count
    # Stages: $match -> $group -> $sort
    # -------------------------------------------------------------
    print("--- 1. Department Revenue & Consultation Summary ---")
    dept_summary_pipeline = [
        {"$match": {"status": "Completed"}},
        {
            "$group": {
                "_id": "$department",
                "total_completed_cases": {"$sum": 1},
                "total_revenue": {"$sum": "$billing.total_amount"},
                "avg_consultation_fee": {"$avg": "$billing.consultation_fee"}
            }
        },
        {"$sort": {"total_revenue": -1}}
    ]

    for record in db.appointments.aggregate(dept_summary_pipeline):
        print(record)

    # -------------------------------------------------------------
    # 2. Pipeline: Medication frequency analysis using $unwind
    # Stages: $unwind -> $group -> $sort -> $limit
    # -------------------------------------------------------------
    print("\n--- 2. Top Prescribed Medicines & Average Dosages ---")
    drug_frequency_pipeline = [
        {"$unwind": "$prescriptions"},
        {
            "$group": {
                "_id": "$prescriptions.medicine_name",
                "times_prescribed": {"$sum": 1},
                "avg_dosage_mg": {"$avg": "$prescriptions.dosage_mg"}
            }
        },
        {"$sort": {"times_prescribed": -1}},
        {"$limit": 5}
    ]

    for record in db.appointments.aggregate(drug_frequency_pipeline):
        print(record)

    # -------------------------------------------------------------
    # 3. Pipeline: Multi-collection Join using $lookup
    # Stages: $match -> $lookup -> $unwind -> $project
    # -------------------------------------------------------------
    print("\n--- 3. Detailed Patient Consultation Dossier ($lookup) ---")
    dossier_pipeline = [
        {"$match": {"appointment_id": "APT-20001"}},
        {
            "$lookup": {
                "from": "patients",
                "localField": "patient_id",
                "foreignField": "patient_id",
                "as": "patient_info"
            }
        },
        {"$unwind": "$patient_info"},
        {
            "$project": {
                "_id": 0,
                "appointment_id": 1,
                "appointment_date": "$date",
                "patient_name": "$patient_info.full_name",
                "patient_email": "$patient_info.email",
                "known_allergies": "$patient_info.allergies",
                "department": 1,
                "total_bill": "$billing.total_amount",
                "prescriptions": 1
            }
        }
    ]

    for record in db.appointments.aggregate(dossier_pipeline):
        print(record)

if __name__ == "__main__":
    run_analytics_pipelines()
    