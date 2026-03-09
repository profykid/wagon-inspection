import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import os
from reportlab.pdfgen import canvas
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# folders
os.makedirs("images", exist_ok=True)
os.makedirs("reports", exist_ok=True)
os.makedirs("signatures", exist_ok=True)

# database
conn = sqlite3.connect("inspections.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS inspections (
id INTEGER PRIMARY KEY AUTOINCREMENT,
wagon TEXT,
datum TEXT,
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

st.set_page_config(page_title="Wagen Inspection", layout="centered")

# styling
st.markdown("""
<style>
.okbox {
background-color:#2ecc71;
color:white;
padding:6px;
border-radius:6px;
text-align:center;
font-weight:bold;
}

.defektbox {
background-color:#e74c3c;
color:white;
padding:6px;
border-radius:6px;
text-align:center;
font-weight:bold;
}
</style>
""", unsafe_allow_html=True)

st.title("🚆 Wagen Inspektion")

# load data
df = pd.read_sql_query("SELECT * FROM inspections", conn)

# ------------------------
# DASHBOARD
# ------------------------

col1,col2,col3 = st.columns(3)

col1.metric("Total Inspektionen", len(df))

defekte = df[df["bremsen"]=="Defekt"].shape[0] + \
          df[df["achse"]=="Defekt"].shape[0] + \
          df[df["kupplung"]=="Defekt"].shape[0] + \
          df[df["federung"]=="Defekt"].shape[0] + \
          df[df["puffer"]=="Defekt"].shape[0] + \
          df[df["rahmen"]=="Defekt"].shape[0]

col2.metric("Gefundene Defekte", defekte)

if len(df)>0:
    wagons = df["wagon"].nunique()
else:
    wagons = 0

col3.metric("Unterschiedliche Wagen", wagons)

tab1, tab2, tab3 = st.tabs(["Neue Inspektion","Historie","Offene Defekte"])

# ------------------------
# CHECK FUNCTION
# ------------------------

def check(name):
    choice = st.radio(name, ["OK","Defekt"], horizontal=True)

    if choice == "OK":
        st.markdown('<div class="okbox">OK</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="defektbox">DEFEKT</div>', unsafe_allow_html=True)

    return choice

# ------------------------
# INSPECTION
# ------------------------

with tab1:

    wagon = st.text_input("Wagennummer")
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

    image = st.file_uploader("Foto hinzufügen")

    image_path = ""

    if image:
        image_path = f"images/{image.name}"
        with open(image_path,"wb") as f:
            f.write(image.getbuffer())

    st.subheader("Unterschrift")

    canvas_result = st_canvas(
        fill_color="black",
        stroke_width=3,
        stroke_color="black",
        background_color="white",
        height=200,
        width=500,
        drawing_mode="freedraw",
        key="canvas"
    )

    signature_path = ""

    if canvas_result.image_data is not None:
        signature_path = f"signatures/sign_{wagon}.png"
        img = Image.fromarray(canvas_result.image_data.astype("uint8"))
        img.save(signature_path)

    if st.button("Inspektion speichern"):

        cursor.execute("""
        INSERT INTO inspections
        (wagon,datum,status,bremsen,achse,kupplung,federung,puffer,rahmen,problem,image,signature)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,(wagon,datum,status,bremsen,achse,kupplung,federung,puffer,rahmen,problem,image_path,signature_path))

        conn.commit()

        st.success("Inspektion gespeichert!")

    if st.button("Neuer Wagen"):
        st.rerun()

# ------------------------
# HISTORY
# ------------------------

with tab2:

    df = pd.read_sql_query("SELECT * FROM inspections ORDER BY id DESC", conn)

    st.dataframe(df)

    if st.button("Export Excel"):

        excel_file = "inspections_export.xlsx"
        df.to_excel(excel_file, index=False)

        st.download_button(
            "Excel herunterladen",
            open(excel_file,"rb"),
            file_name="inspections.xlsx"
        )

# ------------------------
# OPEN DEFECTS
# ------------------------

with tab3:

    df = pd.read_sql_query("SELECT * FROM inspections ORDER BY id DESC", conn)

    defects = df[
        (df["bremsen"]=="Defekt") |
        (df["achse"]=="Defekt") |
        (df["kupplung"]=="Defekt") |
        (df["federung"]=="Defekt") |
        (df["puffer"]=="Defekt") |
        (df["rahmen"]=="Defekt")
    ]

    st.subheader("Offene Defekte")

    st.dataframe(defects)