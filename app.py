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

# -------------------------------------------------
# FOLDERS
# -------------------------------------------------
os.makedirs("images", exist_ok=True)
os.makedirs("signatures", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
users = {
    "admin": "1234",
    "mechanic": "wagon"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("🚆 Wagon Inspection Login")

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

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Wagon Inspection", layout="centered")

# -------------------------------------------------
# DATABASE
# -------------------------------------------------
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

# ---- AUTO COLUMN CHECK ----
cursor.execute("PRAGMA table_info(inspections)")
columns = [col[1] for col in cursor.fetchall()]

required_columns = [
"wagon","datum","mechanic","status",
"bremsen","achse","kupplung","federung",
"puffer","rahmen","problem","image","signature"
]

for col in required_columns:
    if col not in columns:
        cursor.execute(f"ALTER TABLE inspections ADD COLUMN {col} TEXT")

conn.commit()

# -------------------------------------------------
# DATA LOAD
# -------------------------------------------------
@st.cache_data
def load_data():
    return pd.read_sql_query("SELECT * FROM inspections ORDER BY id DESC", conn)

df = load_data()

# -------------------------------------------------
# PDF REPORT
# -------------------------------------------------
def generate_pdf(data):

    filename = f"reports/report_{uuid.uuid4()}.pdf"

    c = pdf_canvas.Canvas(filename)

    c.drawString(100,800,f"Wagon: {data['wagon']}")
    c.drawString(100,780,f"Date: {data['datum']}")
    c.drawString(100,760,f"Mechanic: {data['mechanic']}")
    c.drawString(100,740,f"Status: {data['status']}")

    y = 700

    for key in ["bremsen","achse","kupplung","federung","puffer","rahmen"]:
        c.drawString(100,y,f"{key}: {data[key]}")
        y -= 20

    c.drawString(100,y-20,f"Problem: {data['problem']}")

    c.save()

    return filename

# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
st.title("🚆 Wagen Inspection")

col1,col2,col3 = st.columns(3)

col1.metric("Total Inspektionen", len(df))

defects = df[
(df["bremsen"]=="Defekt") |
(df["achse"]=="Defekt") |
(df["kupplung"]=="Defekt") |
(df["federung"]=="Defekt") |
(df["puffer"]=="Defekt") |
(df["rahmen"]=="Defekt")
]

col2.metric("Gefundene Defekte", len(defects))

wagons = df["wagon"].nunique() if len(df)>0 else 0
col3.metric("Wagen", wagons)

# -------------------------------------------------
# TABS
# -------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
"Neue Inspektion",
"Historie",
"Offene Defekte",
"Statistik"
])

# -------------------------------------------------
# CHECK FUNCTION
# -------------------------------------------------
def check(name):

    choice = st.radio(name,["OK","Defekt"],horizontal=True,key=name)

    if choice == "OK":
        st.success("OK")
    else:
        st.error("DEFEKT")

    return choice

# -------------------------------------------------
# NEW INSPECTION
# -------------------------------------------------
with tab1:

    wagon = st.text_input("Wagennummer")
    mechanic = st.text_input("Mechaniker Name", value=st.session_state.user)

    datum = st.date_input("Datum", date.today())

    status = st.selectbox(
        "Status Wagen",
        ["OK","In Reparatur","Gesperrt"]
    )

    st.subheader("Checkliste")

    bremsen = check("Bremsen")
    achse = check("Achse")
    kupplung = check("Kupplung")
    federung = check("Federung")
    puffer = check("Puffer")
    rahmen = check("Rahmen")

    problem = st.text_area("Problem Beschreibung")

    # FOTO
    st.subheader("Foto")

    image = st.camera_input("Foto aufnehmen")

    image_path = ""

    if image:
        filename = f"{uuid.uuid4()}.png"
        image_path = f"images/{filename}"

        with open(image_path,"wb") as f:
            f.write(image.getbuffer())

        st.image(image)

    # SIGNATURE
    st.subheader("Unterschrift")

    canvas_result = st_canvas(
        fill_color="black",
        stroke_width=3,
        stroke_color="black",
        background_color="white",
        height=200,
        width=500,
        drawing_mode="freedraw",
        key="signature"
    )

    if st.button("Inspektion speichern"):

        if wagon == "":
            st.warning("Bitte Wagennummer eingeben")
            st.stop()

        signature_path = ""

        if canvas_result.image_data is not None:
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

        pdf = generate_pdf({
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

        st.success("Inspektion gespeichert")

        with open(pdf,"rb") as f:
            st.download_button("Download PDF Report",f,file_name="report.pdf")

        st.cache_data.clear()
        st.rerun()

# -------------------------------------------------
# HISTORY
# -------------------------------------------------
with tab2:

    search = st.text_input("Wagon suchen")

    if search:
        filtered = df[df["wagon"].str.contains(search)]
    else:
        filtered = df

    st.dataframe(filtered)

    if st.button("Export Excel"):

        file = "inspections_export.xlsx"
        filtered.to_excel(file,index=False)

        st.download_button(
            "Download Excel",
            open(file,"rb"),
            file_name="inspections.xlsx"
        )

# -------------------------------------------------
# OPEN DEFECTS
# -------------------------------------------------
with tab3:

    st.subheader("Offene Defekte")

    defects = df[
        (df["bremsen"]=="Defekt") |
        (df["achse"]=="Defekt") |
        (df["kupplung"]=="Defekt") |
        (df["federung"]=="Defekt") |
        (df["puffer"]=="Defekt") |
        (df["rahmen"]=="Defekt")
    ]

    st.dataframe(defects)

# -------------------------------------------------
# STATISTICS
# -------------------------------------------------
with tab4:

    st.subheader("Defekt Statistik")

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
