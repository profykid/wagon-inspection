import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import os
import uuid
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import plotly.express as px
from reportlab.pdfgen import canvas as pdf_canvas

# --------------------------------------------------
# FOLDERS
# --------------------------------------------------

os.makedirs("images", exist_ok=True)
os.makedirs("signatures", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# --------------------------------------------------
# LOGIN
# --------------------------------------------------

users = {
    "admin": "1234",
    "mechanic": "wagon"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("Wagon Inspection Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if username in users and users[username] == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Wrong login")

    st.stop()

# --------------------------------------------------
# PAGE
# --------------------------------------------------

st.set_page_config(page_title="Wagon Inspection", layout="centered")

st.sidebar.write(f"Logged in: **{st.session_state.user}**")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

conn = sqlite3.connect("inspections.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS inspections (
id INTEGER PRIMARY KEY AUTOINCREMENT,
wagon TEXT,
datum TEXT,
mechanic TEXT,
status TEXT,
bremsen TEXT,
achse TEXT,
kupplung TEXT,
federung TEXT,
puffer TEXT,
rahmen TEXT,
problem TEXT,
image TEXT,
signature TEXT
)
""")

conn.commit()

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data
def load_data():
    return pd.read_sql_query("SELECT * FROM inspections ORDER BY id DESC", conn)

df = load_data()

# --------------------------------------------------
# PDF
# --------------------------------------------------

def generate_pdf(data):

    filename = f"reports/report_{uuid.uuid4()}.pdf"

    c = pdf_canvas.Canvas(filename)

    c.setFont("Helvetica-Bold",16)
    c.drawString(100,820,"Wagon Inspection Report")

    c.setFont("Helvetica",12)

    c.drawString(100,790,f"Wagon: {data['wagon']}")
    c.drawString(100,770,f"Date: {data['datum']}")
    c.drawString(100,750,f"Mechanic: {data['mechanic']}")
    c.drawString(100,730,f"Status: {data['status']}")

    y = 700

    for key in ["bremsen","achse","kupplung","federung","puffer","rahmen"]:
        c.drawString(100,y,f"{key}: {data[key]}")
        y -= 20

    c.drawString(100,y-20,"Problem / Nalog")

    text = c.beginText(100,y-40)
    text.textLines(data["problem"])
    c.drawText(text)

    c.save()

    return filename

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

st.title("🚆 Wagon Inspection")

col1,col2,col3 = st.columns(3)

col1.metric("Total Inspections", len(df))

defects = df[
(df["bremsen"]=="Defekt") |
(df["achse"]=="Defekt") |
(df["kupplung"]=="Defekt") |
(df["federung"]=="Defekt") |
(df["puffer"]=="Defekt") |
(df["rahmen"]=="Defekt")
]

col2.metric("Defects", len(defects))

wagons = df["wagon"].nunique() if len(df)>0 else 0
col3.metric("Wagons", wagons)

tab1, tab2, tab3, tab4 = st.tabs([
"Neue Inspektion",
"Historie",
"Defekte",
"Statistik"
])

# --------------------------------------------------
# CHECK FUNCTION
# --------------------------------------------------

def check(name):

    return st.radio(
        name,
        ["OK","Defekt"],
        horizontal=True,
        key=name
    )

# --------------------------------------------------
# INSPECTION
# --------------------------------------------------

with tab1:

    wagon = st.text_input("Wagennummer")
    mechanic = st.text_input("Mechaniker", value=st.session_state.user)

    datum = st.date_input("Datum", date.today())

    status = st.selectbox("Status", ["OK","In Reparatur","Gesperrt"])

    st.subheader("Checkliste")

    bremsen = check("bremsen")
    achse = check("achse")
    kupplung = check("kupplung")
    federung = check("federung")
    puffer = check("puffer")
    rahmen = check("rahmen")

    problem = st.text_area("Problem / Nalog")

    st.subheader("Foto")

    image = st.camera_input("Foto aufnehmen")

    image_path = ""

    if image:

        filename = f"{uuid.uuid4()}.png"
        image_path = f"images/{filename}"

        with open(image_path,"wb") as f:
            f.write(image.getbuffer())

    st.subheader("Unterschrift")

    if "sign_mode" not in st.session_state:
        st.session_state.sign_mode = False

    signature_path = ""

    if not st.session_state.sign_mode:

        if st.button("Start Signing"):
            st.session_state.sign_mode = True
            st.rerun()

    else:

        canvas_result = st_canvas(
            fill_color="black",
            stroke_width=3,
            stroke_color="black",
            background_color="white",
            height=200,
            width=500,
            drawing_mode="freedraw",
        )

        if st.button("Clear Signature"):
            st.session_state.sign_mode = False
            st.rerun()

    # SAVE

    if st.button("Save Inspection"):

        if wagon.strip() == "":
            st.error("Wagennummer ist erforderlich")
            st.stop()

        if not st.session_state.sign_mode:
            st.error("Bitte unterschreiben")
            st.stop()

        if canvas_result.image_data is None:
            st.error("Bitte unterschreiben")
            st.stop()

        signature_path = f"signatures/{uuid.uuid4()}.png"

        img = Image.fromarray(canvas_result.image_data.astype("uint8"))
        img.save(signature_path)

        cursor.execute("""
        INSERT INTO inspections
        (wagon,datum,mechanic,status,bremsen,achse,kupplung,federung,puffer,rahmen,problem,image,signature)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,(
        wagon,datum,mechanic,status,
        bremsen,achse,kupplung,federung,
        puffer,rahmen,problem,image_path,signature_path
        ))

        conn.commit()

        pdf_file = generate_pdf({
            "wagon":wagon,
            "datum":datum,
            "mechanic":mechanic,
            "status":status,
            "bremsen":bremsen,
            "achse":achse,
            "kupplung":kupplung,
            "federung":federung,
            "puffer":puffer,
            "rahmen":rahmen,
            "problem":problem
        })

        st.session_state["last_pdf"] = pdf_file

        st.success("Inspection saved")

        st.session_state.sign_mode = False
        st.cache_data.clear()

# --------------------------------------------------
# PDF DOWNLOAD
# --------------------------------------------------

if "last_pdf" in st.session_state:

    with open(st.session_state["last_pdf"], "rb") as f:

        st.download_button(
            "Download PDF Report",
            f,
            file_name="inspection_report.pdf"
        )

# --------------------------------------------------
# HISTORY
# --------------------------------------------------

with tab2:

    st.dataframe(df)

# --------------------------------------------------
# DEFECTS
# --------------------------------------------------

with tab3:

    st.dataframe(defects)

# --------------------------------------------------
# STATISTICS
# --------------------------------------------------

with tab4:

    defect_counts = {
        "Bremsen":(df["bremsen"]=="Defekt").sum(),
        "Achse":(df["achse"]=="Defekt").sum(),
        "Kupplung":(df["kupplung"]=="Defekt").sum(),
        "Federung":(df["federung"]=="Defekt").sum(),
        "Puffer":(df["puffer"]=="Defekt").sum(),
        "Rahmen":(df["rahmen"]=="Defekt").sum()
    }

    chart_df = pd.DataFrame({
        "Teil": defect_counts.keys(),
        "Defekte": defect_counts.values()
    })

    fig = px.bar(chart_df, x="Teil", y="Defekte")

    st.plotly_chart(fig)
