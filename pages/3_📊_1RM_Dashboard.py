import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📊 Global 1RM Dashboard")

# Fetch all exercises with history
history = supabase.table("exercise_maxes") \
    .select("*") \
    .order("date", desc=True) \
    .execute().data

if not history:
    st.warning("No 1RM data available yet.")
else:
    df = pd.DataFrame(history)
    exercises = df["exercise_name"].unique()

    for ex in exercises:
        st.subheader(ex)
        ex_df = df[df["exercise_name"] == ex].copy()
        ex_df["date"] = pd.to_datetime(ex_df["date"])
        ex_df["max_used"] = ex_df.apply(lambda r: r["manual_1rm"] if r["manual_1rm"] else r["calculated_1rm"], axis=1)

        current_max = ex_df.iloc[0]["max_used"]
        st.markdown(f"**Current 1RM:** {current_max} kg")

        st.line_chart(ex_df.set_index("date")["max_used"])

        # Manual override input
        manual_input = st.number_input(f"Enter manual 1RM for {ex}", min_value=0.0, step=0.5, key=f"manual_{ex}")
        if st.button(f"💾 Save Manual 1RM for {ex}", key=f"save_{ex}"):
            supabase.table("exercise_maxes").insert({
                "exercise_name": ex,
                "manual_1rm": manual_input,
                "date": datetime.now().isoformat()
            }).execute()
            st.success(f"Manual 1RM for {ex} saved!")
            st.rerun()
