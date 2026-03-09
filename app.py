import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import os
import uuid
from PIL import Image

# --------------------------------------------------
# FOLDERS
# --------------------------------------------------

os.makedirs("images", exist_ok=True)

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
images TEXT
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
# DASHBOARD
# --------------------------------------------------

st.title("🚆 Wagon Inspection")

tab1, tab2 = st.tabs([
"Neue Inspektion",
"Historie"
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
# NEW INSPECTION
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

    # ----------------------------------------
    # MULTIPLE IMAGES
    # ----------------------------------------

    st.subheader("Fotos")

    images = st.file_uploader(
        "Fotos hochladen",
        type=["png","jpg","jpeg"],
        accept_multiple_files=True
    )

    image_paths = []

    if images:

        for img in images:

            filename = f"{uuid.uuid4()}.png"
            path = f"images/{filename}"

            with open(path,"wb") as f:
                f.write(img.getbuffer())

            image_paths.append(path)

        st.success(f"{len(image_paths)} image(s) ready")

    # ----------------------------------------
    # SAVE
    # ----------------------------------------

    if st.button("Save Inspection"):

        if wagon.strip() == "":
            st.error("Wagennummer ist erforderlich")
            st.stop()

        image_string = ",".join(image_paths)

        cursor.execute("""
        INSERT INTO inspections
        (wagon,datum,mechanic,status,bremsen,achse,kupplung,federung,puffer,rahmen,problem,images)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,(
        wagon,datum,mechanic,status,
        bremsen,achse,kupplung,federung,
        puffer,rahmen,problem,image_string
        ))

        conn.commit()

        st.success("Inspection saved")

        st.cache_data.clear()

# --------------------------------------------------
# HISTORY
# --------------------------------------------------

with tab2:

    st.subheader("Inspection History")

    for index,row in df.iterrows():

        with st.expander(f"Wagon {row['wagon']} | {row['datum']}"):

            st.write("Mechanic:", row["mechanic"])
            st.write("Status:", row["status"])

            st.write("Bremsen:", row["bremsen"])
            st.write("Achse:", row["achse"])
            st.write("Kupplung:", row["kupplung"])
            st.write("Federung:", row["federung"])
            st.write("Puffer:", row["puffer"])
            st.write("Rahmen:", row["rahmen"])

            st.write("Problem:", row["problem"])

            # -----------------------------
            # SHOW IMAGES
            # -----------------------------

            if row["images"]:

                paths = row["images"].split(",")

                st.write("Fotos:")

                cols = st.columns(3)

                for i,p in enumerate(paths):
                    cols[i % 3].image(p, use_column_width=True)