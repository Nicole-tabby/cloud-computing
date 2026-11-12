import os
import re
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


@app.route("/")
def home():
    return redirect(url_for("register_doctor"))


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

@app.route("/appointments/book", methods=["GET", "POST"])
def book_appointment():
    if request.method == "POST":
        doctor_id = ObjectId(request.form["doctor_id"])
        patient = patients.find_one({"_id": ObjectId(request.form["patient_id"])})
        date = request.form["date"]
        time = request.form["time"]

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
    return render_template("search.html", results=results,
                           q=request.args)


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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")