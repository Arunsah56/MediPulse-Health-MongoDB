import os
from datetime import datetime
from functools import wraps

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError, WriteError

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "MediPulseHealth"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-local-dev-secret")

if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI was not found. Add it to a .env file in the project root."
    )

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=7000)
db = client[DB_NAME]
patients = db["patients"]
appointments = db["appointments"]

DEPARTMENTS = [
    "Cardiology", "Neurology", "Pediatrics", "Orthopedics",
    "General Medicine"
]
STATUSES = ["Scheduled", "Completed", "Cancelled"]
GENDERS = ["Male", "Female", "Other"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
PAYMENT_STATUSES = ["Paid", "Pending", "Claimed"]


@app.template_filter("money")
def money(value):
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


@app.template_filter("date_display")
def date_display(value):
    return value or "Not set"


def check_connection():
    client.admin.command("ping")


def safe_object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def next_code(collection, field, prefix):
    """Generate the next PAT-xxxxx or APT-xxxxx identifier."""
    existing = list(collection.find(
        {field: {"$regex": f"^{prefix}-[0-9]+$"}},
        {field: 1, "_id": 0}
    ))
    highest = 10000 if prefix == "PAT" else 20000
    for item in existing:
        try:
            highest = max(highest, int(item[field].split("-")[-1]))
        except (ValueError, AttributeError):
            continue
    return f"{prefix}-{highest + 1}"


def get_patient_choices():
    return list(patients.find({}, {"patient_id": 1, "full_name": 1, "_id": 0}).sort("full_name", 1))


def parse_float(value, field_label):
    try:
        result = float(value)
        if result < 0:
            raise ValueError
        return result
    except (TypeError, ValueError):
        raise ValueError(f"{field_label} must be a number greater than or equal to 0.")


def parse_int(value, field_label, minimum=1):
    try:
        result = int(value)
        if result < minimum:
            raise ValueError
        return result
    except (TypeError, ValueError):
        raise ValueError(f"{field_label} must be a whole number of at least {minimum}.")


@app.route("/")
def dashboard():
    try:
        check_connection()
        patient_count = patients.count_documents({})
        appointment_count = appointments.count_documents({})
        completed_count = appointments.count_documents({"status": "Completed"})
        scheduled_count = appointments.count_documents({"status": "Scheduled"})

        revenue_rows = list(appointments.aggregate([
            {"$match": {"status": "Completed"}},
            {"$group": {
                "_id": "$department",
                "total_revenue": {"$sum": "$billing.total_amount"},
                "completed_cases": {"$sum": 1},
                "avg_consultation_fee": {"$avg": "$billing.consultation_fee"}
            }},
            {"$sort": {"total_revenue": -1}}
        ]))
        total_revenue = sum(row.get("total_revenue", 0) or 0 for row in revenue_rows)

        medicine_rows = list(appointments.aggregate([
            {"$unwind": {"path": "$prescriptions", "preserveNullAndEmptyArrays": False}},
            {"$group": {
                "_id": "$prescriptions.medicine_name",
                "times_prescribed": {"$sum": 1},
                "avg_dosage_mg": {"$avg": "$prescriptions.dosage_mg"}
            }},
            {"$sort": {"times_prescribed": -1, "_id": 1}},
            {"$limit": 5}
        ]))

        recent_appointments = list(appointments.find().sort("_id", -1).limit(6))
        patient_map = {
            p.get("patient_id"): p.get("full_name", "Unknown patient")
            for p in patients.find({}, {"patient_id": 1, "full_name": 1, "_id": 0})
        }
        for appt in recent_appointments:
            appt["patient_name"] = patient_map.get(appt.get("patient_id"), "Patient not found")

        # Data for the dashboard's lightweight chart.
        chart_labels = [r.get("_id", "Other") for r in revenue_rows]
        chart_values = [float(r.get("total_revenue", 0) or 0) for r in revenue_rows]

        return render_template(
            "dashboard.html",
            page="dashboard",
            patient_count=patient_count,
            appointment_count=appointment_count,
            completed_count=completed_count,
            scheduled_count=scheduled_count,
            total_revenue=total_revenue,
            revenue_rows=revenue_rows,
            medicine_rows=medicine_rows,
            recent_appointments=recent_appointments,
            chart_labels=chart_labels,
            chart_values=chart_values,
        )
    except PyMongoError as exc:
        app.logger.exception("MongoDB dashboard query failed")
        flash("Could not load dashboard data. Check your Atlas connection and database permissions.", "error")
        return render_template(
            "dashboard.html", page="dashboard", connection_error=True,
            patient_count=0, appointment_count=0, completed_count=0,
            scheduled_count=0, total_revenue=0, revenue_rows=[],
            medicine_rows=[], recent_appointments=[], chart_labels=[],
            chart_values=[]
        )


@app.route("/patients")
def patient_list():
    search = request.args.get("q", "").strip()
    query = {}
    if search:
        query = {"$or": [
            {"patient_id": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]}
    rows = list(patients.find(query).sort("full_name", 1))
    return render_template("patients.html", page="patients", patients=rows, search=search)


@app.route("/patients/new", methods=["GET", "POST"])
def patient_new():
    if request.method == "POST":
        try:
            patient_id = request.form.get("patient_id", "").strip().upper() or next_code(patients, "patient_id", "PAT")
            record = {
                "patient_id": patient_id,
                "full_name": request.form.get("full_name", "").strip(),
                "email": request.form.get("email", "").strip(),
                "gender": request.form.get("gender", ""),
                "dob": request.form.get("dob", "").strip(),
                "contact": request.form.get("contact", "").strip(),
                "blood_group": request.form.get("blood_group", ""),
                "allergies": [x.strip() for x in request.form.get("allergies", "").split(",") if x.strip()],
            }
            if not all(record.get(k) for k in ["patient_id", "full_name", "email", "gender", "dob", "contact"]):
                raise ValueError("Please complete all required patient fields.")
            if len(record["full_name"]) < 3:
                raise ValueError("Patient name must contain at least 3 characters.")
            datetime.strptime(record["dob"], "%Y-%m-%d")
            if patients.find_one({"patient_id": patient_id}):
                raise ValueError(f"Patient ID {patient_id} already exists.")
            patients.insert_one(record)
            flash(f"Patient {patient_id} was added.", "success")
            return redirect(url_for("patient_list"))
        except (ValueError, WriteError, PyMongoError) as exc:
            flash(f"Could not add patient: {exc}", "error")
    return render_template("patient_form.html", page="patients", patient=None, genders=GENDERS, blood_groups=BLOOD_GROUPS)


@app.route("/patients/<record_id>/edit", methods=["GET", "POST"])
def patient_edit(record_id):
    oid = safe_object_id(record_id)
    patient = patients.find_one({"_id": oid}) if oid else None
    if not patient:
        flash("Patient record not found.", "error")
        return redirect(url_for("patient_list"))
    if request.method == "POST":
        try:
            patient_id = request.form.get("patient_id", "").strip().upper()
            record = {
                "patient_id": patient_id,
                "full_name": request.form.get("full_name", "").strip(),
                "email": request.form.get("email", "").strip(),
                "gender": request.form.get("gender", ""),
                "dob": request.form.get("dob", "").strip(),
                "contact": request.form.get("contact", "").strip(),
                "blood_group": request.form.get("blood_group", ""),
                "allergies": [x.strip() for x in request.form.get("allergies", "").split(",") if x.strip()],
            }
            if not all(record.get(k) for k in ["patient_id", "full_name", "email", "gender", "dob", "contact"]):
                raise ValueError("Please complete all required patient fields.")
            datetime.strptime(record["dob"], "%Y-%m-%d")
            duplicate = patients.find_one({"patient_id": patient_id, "_id": {"$ne": oid}})
            if duplicate:
                raise ValueError(f"Patient ID {patient_id} already exists.")
            patients.update_one({"_id": oid}, {"$set": record})
            flash(f"Patient {patient_id} was updated.", "success")
            return redirect(url_for("patient_list"))
        except (ValueError, WriteError, PyMongoError) as exc:
            flash(f"Could not update patient: {exc}", "error")
            patient.update({
                "patient_id": request.form.get("patient_id", ""),
                "full_name": request.form.get("full_name", ""),
                "email": request.form.get("email", ""),
                "gender": request.form.get("gender", ""),
                "dob": request.form.get("dob", ""),
                "contact": request.form.get("contact", ""),
                "blood_group": request.form.get("blood_group", ""),
                "allergies": [x.strip() for x in request.form.get("allergies", "").split(",") if x.strip()],
            })
    return render_template("patient_form.html", page="patients", patient=patient, genders=GENDERS, blood_groups=BLOOD_GROUPS)


@app.route("/patients/<record_id>/delete", methods=["POST"])
def patient_delete(record_id):
    oid = safe_object_id(record_id)
    patient = patients.find_one({"_id": oid}) if oid else None
    if not patient:
        flash("Patient record not found.", "error")
    elif appointments.count_documents({"patient_id": patient.get("patient_id")}):
        flash("This patient has appointments. Delete or reassign those appointments first.", "error")
    else:
        patients.delete_one({"_id": oid})
        flash(f"Patient {patient.get('patient_id')} was deleted.", "success")
    return redirect(url_for("patient_list"))


@app.route("/appointments")
def appointment_list():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = {}
    if status in STATUSES:
        query["status"] = status
    if search:
        query["$or"] = [
            {"appointment_id": {"$regex": search, "$options": "i"}},
            {"patient_id": {"$regex": search, "$options": "i"}},
            {"department": {"$regex": search, "$options": "i"}},
        ]
    rows = list(appointments.find(query).sort("date", -1))
    patient_map = {p.get("patient_id"): p.get("full_name", "Unknown") for p in patients.find({}, {"patient_id": 1, "full_name": 1, "_id": 0})}
    for row in rows:
        row["patient_name"] = patient_map.get(row.get("patient_id"), "Patient not found")
    return render_template("appointments.html", page="appointments", appointments=rows, search=search, status_filter=status)


def appointment_form_values(form):
    appointment_id = form.get("appointment_id", "").strip().upper()
    patient_id = form.get("patient_id", "").strip()
    doctor_id = form.get("doctor_id", "").strip()
    department = form.get("department", "")
    date_value = form.get("date", "").strip()
    status = form.get("status", "")
    payment_status = form.get("payment_status", "")
    if not all([patient_id, doctor_id, department, date_value, status, payment_status]):
        raise ValueError("Please complete all required appointment fields.")
    datetime.strptime(date_value, "%Y-%m-%d")
    if not patients.find_one({"patient_id": patient_id}):
        raise ValueError("Select an existing patient.")
    consultation_fee = parse_float(form.get("consultation_fee"), "Consultation fee")
    medication_fee = parse_float(form.get("medication_fee"), "Medication fee")
    prescriptions = []
    names = form.getlist("medicine_name[]")
    dosages = form.getlist("dosage_mg[]")
    durations = form.getlist("duration_days[]")
    for name, dosage, duration in zip(names, dosages, durations):
        name = name.strip()
        if not name and not dosage and not duration:
            continue
        if not name:
            raise ValueError("Enter a medicine name for each prescription row.")
        prescriptions.append({
            "medicine_name": name,
            "dosage_mg": parse_int(dosage, "Dosage (mg)"),
            "duration_days": parse_int(duration, "Duration (days)")
        })
    return {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "department": department,
        "date": date_value,
        "status": status,
        "billing": {
            "consultation_fee": consultation_fee,
            "medication_fee": medication_fee,
            "total_amount": consultation_fee + medication_fee,
            "payment_status": payment_status,
        },
        "prescriptions": prescriptions,
    }


@app.route("/appointments/new", methods=["GET", "POST"])
def appointment_new():
    if not get_patient_choices():
        flash("Add a patient before creating an appointment.", "error")
        return redirect(url_for("patient_new"))
    if request.method == "POST":
        try:
            record = appointment_form_values(request.form)
            record["appointment_id"] = record["appointment_id"] or next_code(appointments, "appointment_id", "APT")
            if appointments.find_one({"appointment_id": record["appointment_id"]}):
                raise ValueError(f"Appointment ID {record['appointment_id']} already exists.")
            appointments.insert_one(record)
            flash(f"Appointment {record['appointment_id']} was added.", "success")
            return redirect(url_for("appointment_list"))
        except (ValueError, WriteError, PyMongoError) as exc:
            flash(f"Could not add appointment: {exc}", "error")
    return render_template("appointment_form.html", page="appointments", appointment=None, patients=get_patient_choices(), departments=DEPARTMENTS, statuses=STATUSES, payment_statuses=PAYMENT_STATUSES)


@app.route("/appointments/<record_id>/edit", methods=["GET", "POST"])
def appointment_edit(record_id):
    oid = safe_object_id(record_id)
    appointment = appointments.find_one({"_id": oid}) if oid else None
    if not appointment:
        flash("Appointment record not found.", "error")
        return redirect(url_for("appointment_list"))
    if request.method == "POST":
        try:
            record = appointment_form_values(request.form)
            duplicate = appointments.find_one({"appointment_id": record["appointment_id"], "_id": {"$ne": oid}}) if record["appointment_id"] else None
            if duplicate:
                raise ValueError(f"Appointment ID {record['appointment_id']} already exists.")
            record["appointment_id"] = record["appointment_id"] or appointment["appointment_id"]
            appointments.update_one({"_id": oid}, {"$set": record})
            flash(f"Appointment {record['appointment_id']} was updated.", "success")
            return redirect(url_for("appointment_list"))
        except (ValueError, WriteError, PyMongoError) as exc:
            flash(f"Could not update appointment: {exc}", "error")
    return render_template("appointment_form.html", page="appointments", appointment=appointment, patients=get_patient_choices(), departments=DEPARTMENTS, statuses=STATUSES, payment_statuses=PAYMENT_STATUSES)


@app.route("/appointments/<record_id>/delete", methods=["POST"])
def appointment_delete(record_id):
    oid = safe_object_id(record_id)
    result = appointments.delete_one({"_id": oid}) if oid else None
    flash("Appointment deleted." if result and result.deleted_count else "Appointment record not found.", "success" if result and result.deleted_count else "error")
    return redirect(url_for("appointment_list"))


@app.route("/health")
def health():
    try:
        check_connection()
        return {"status": "ok", "database": DB_NAME}, 200
    except PyMongoError:
        return {"status": "error", "message": "Database connection unavailable"}, 503


if __name__ == "__main__":
    app.run(debug=True)