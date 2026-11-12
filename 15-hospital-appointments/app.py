import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")