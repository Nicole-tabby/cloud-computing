import os
import re
import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-secret")

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME", "hospital_db")]
doctors = db["doctors"]
patients = db["patients"]


def patient_has_conflict(patient_id, date, time, exclude_appt_id=None):
    """True if this patient already has a Booked appointment at this date/time with ANY doctor."""
    elem = {"patient_id": patient_id, "date": date, "time": time, "status": "Booked"}
    if exclude_appt_id:
        elem["_id"] = {"$ne": ObjectId(exclude_appt_id)}
    return doctors.find_one({"appointments": {"$elemMatch": elem}}) is not None


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/doctors/register", methods=["GET", "POST"])
def register_doctor():
    if request.method == "POST":
        name = request.form["name"].strip()
        specialization = request.form["specialization"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()

        if not name or not specialization:
            flash("Name and specialization are required.", "danger")
        else:
            doctors.insert_one({
                "doctor": name,
                "specialization": specialization,
                "email": email,
                "phone": phone,
                "appointments": []
            })
            flash(f"{name} registered successfully.", "success")
        return redirect(url_for("register_doctor"))

    return render_template("register_doctor.html", doctors=list(doctors.find()))


@app.route("/doctors/<doctor_id>/delete", methods=["POST"])
def delete_doctor(doctor_id):
    doc = doctors.find_one({"_id": ObjectId(doctor_id)})
    if not doc:
        flash("Doctor not found.", "danger")
        return redirect(url_for("register_doctor"))

    # Block removal while patients still hold upcoming bookings with this doctor
    today = datetime.date.today().isoformat()
    upcoming = [a for a in doc.get("appointments", [])
                if a.get("status") == "Booked" and a.get("date", "") >= today]
    if upcoming:
        flash(f"{doc['doctor']} still has {len(upcoming)} upcoming booked appointment(s). "
              "Cancel or reschedule them first, then delete the doctor.", "danger")
        return redirect(url_for("register_doctor"))

    doctors.delete_one({"_id": doc["_id"]})
    flash(f"{doc['doctor']} was removed.", "secondary")
    return redirect(url_for("register_doctor"))


@app.route("/patients/register", methods=["GET", "POST"])
def register_patient():
    if request.method == "POST":
        name = request.form["name"].strip()
        age = request.form["age"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip()

        if not name or not age.isdigit():
            flash("Name and a numeric age are required.", "danger")
        else:
            patients.insert_one({
                "name": name,
                "age": int(age),
                "phone": phone,
                "email": email
            })
            flash(f"{name} registered successfully.", "success")
        return redirect(url_for("register_patient"))

    return render_template("register_patient.html", patients=list(patients.find()))


@app.route("/patients/<patient_id>/delete", methods=["POST"])
def delete_patient(patient_id):
    pid = ObjectId(patient_id)
    patient = patients.find_one({"_id": pid})
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("register_patient"))

    # Appointments are embedded inside doctor documents, so remove them there too.
    # Otherwise the patient's name would stay behind in the nested data.
    removed = sum(1 for d in doctors.find({"appointments.patient_id": pid})
                  for a in d["appointments"] if a.get("patient_id") == pid)
    doctors.update_many({"appointments.patient_id": pid},
                        {"$pull": {"appointments": {"patient_id": pid}}})
    patients.delete_one({"_id": pid})

    flash(f"{patient['name']} was removed, along with {removed} appointment(s).", "secondary")
    return redirect(url_for("register_patient"))


@app.route("/appointments/book", methods=["GET", "POST"])
def book_appointment():
    if request.method == "POST":
        doctor_id = ObjectId(request.form["doctor_id"])
        patient = patients.find_one({"_id": ObjectId(request.form["patient_id"])})
        date = request.form["date"]
        time = request.form["time"]

        if patient_has_conflict(patient["_id"], date, time):
            flash(f"{patient['name']} already has an appointment at that date and time.", "danger")
            return redirect(url_for("book_appointment"))

        appt = {
            "_id": ObjectId(),
            "patient_id": patient["_id"],
            "patient": patient["name"],
            "date": date,
            "time": time,
            "status": "Booked"
        }
        # Push only if this doctor has no active booking at the same date and time
        result = doctors.update_one(
            {"_id": doctor_id,
             "appointments": {"$not": {"$elemMatch": {
                 "date": date, "time": time, "status": "Booked"}}}},
            {"$push": {"appointments": appt}}
        )
        if result.modified_count:
            flash("Appointment booked.", "success")
        else:
            flash("That slot is already taken for this doctor.", "danger")
        return redirect(url_for("book_appointment"))

    return render_template("book.html",
                           doctors=list(doctors.find()),
                           patients=list(patients.find()))


@app.route("/appointments/search")
def search_appointments():
    doctor = request.args.get("doctor", "").strip()
    specialization = request.args.get("specialization", "").strip()
    patient = request.args.get("patient", "").strip()
    date = request.args.get("date", "").strip()

    match = {}
    if doctor:
        match["doctor"] = {"$regex": re.escape(doctor), "$options": "i"}
    if specialization:
        match["specialization"] = {"$regex": re.escape(specialization), "$options": "i"}
    if patient:
        match["appointments.patient"] = {"$regex": re.escape(patient), "$options": "i"}
    if date:
        match["appointments.date"] = date

    pipeline = [{"$unwind": "$appointments"}, {"$match": match},
                {"$sort": {"appointments.date": 1, "appointments.time": 1}}]
    results = list(doctors.aggregate(pipeline))
    return render_template("search.html", results=results, q=request.args)


@app.route("/appointments/<doctor_id>/<appt_id>/cancel", methods=["POST"])
def cancel_appointment(doctor_id, appt_id):
    doctors.update_one(
        {"_id": ObjectId(doctor_id), "appointments._id": ObjectId(appt_id)},
        {"$set": {"appointments.$.status": "Cancelled"}}
    )
    flash("Appointment cancelled.", "warning")
    return redirect(request.referrer or url_for("search_appointments"))


@app.route("/appointments/<doctor_id>/<appt_id>/delete", methods=["POST"])
def delete_appointment(doctor_id, appt_id):
    doctors.update_one(
        {"_id": ObjectId(doctor_id)},
        {"$pull": {"appointments": {"_id": ObjectId(appt_id)}}}
    )
    flash("Appointment deleted.", "secondary")
    return redirect(request.referrer or url_for("search_appointments"))


@app.route("/dashboard")
def dashboard():
    today = datetime.date.today().isoformat()

    status_counts = {r["_id"]: r["count"] for r in doctors.aggregate([
        {"$unwind": "$appointments"},
        {"$group": {"_id": "$appointments.status", "count": {"$sum": 1}}}
    ])}

    upcoming = list(doctors.aggregate([
        {"$unwind": "$appointments"},
        {"$match": {"appointments.status": "Booked",
                    "appointments.date": {"$gte": today}}},
        {"$sort": {"appointments.date": 1, "appointments.time": 1}},
        {"$limit": 10}
    ]))

    per_doctor = list(doctors.aggregate([
        {"$project": {"doctor": 1, "specialization": 1,
                      "booked": {"$size": {"$filter": {
                          "input": "$appointments", "as": "a",
                          "cond": {"$eq": ["$$a.status", "Booked"]}}}}}}
    ]))

    return render_template("dashboard.html",
                           total_doctors=doctors.count_documents({}),
                           total_patients=patients.count_documents({}),
                           status_counts=status_counts,
                           upcoming=upcoming,
                           per_doctor=per_doctor)


@app.route("/appointments/<doctor_id>/<appt_id>/reschedule", methods=["GET", "POST"])
def reschedule_appointment(doctor_id, appt_id):
    doc = doctors.find_one({"_id": ObjectId(doctor_id)})
    appt = None
    if doc:
        appt = next((a for a in doc["appointments"] if str(a["_id"]) == appt_id), None)
    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for("search_appointments"))

    if request.method == "POST":
        new_date = request.form["date"]
        new_time = request.form["time"]
        conflict = any(
            a["date"] == new_date and a["time"] == new_time
            and a["status"] == "Booked" and str(a["_id"]) != appt_id
            for a in doc["appointments"])
        if conflict:
            flash("That slot is already taken for this doctor.", "danger")
        elif patient_has_conflict(appt["patient_id"], new_date, new_time, exclude_appt_id=appt_id):
            flash(f"{appt['patient']} already has an appointment at that date and time.", "danger")
        else:
            doctors.update_one(
                {"_id": ObjectId(doctor_id), "appointments._id": ObjectId(appt_id)},
                {"$set": {"appointments.$.date": new_date,
                          "appointments.$.time": new_time,
                          "appointments.$.status": "Booked"}})
            flash("Appointment rescheduled.", "success")
            return redirect(url_for("search_appointments"))

    return render_template("reschedule.html", doctor=doc, appt=appt)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
