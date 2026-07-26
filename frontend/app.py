# frontend/app.py
import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Text-to-SQL AI Engine",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Guardrailed Text-to-SQL AI Engine")
st.caption("Natural language interface with safety guardrails, back-translation verification, and confidence scoring.")

# Sidebar for Database Schema & History
with st.sidebar:
    st.header("⚙️ System Control")
    if st.button("Refresh Database Schema"):
        try:
            res = requests.get(f"{API_URL}/v1/schema")
            if res.status_code == 200:
                st.success("Schema synchronized successfully!")
                st.json(res.json())
        except Exception as e:
            st.error(f"Backend connection error: {e}")

    st.markdown("---")
    st.subheader("📜 Query History")
    try:
        hist_res = requests.get(f"{API_URL}/v1/history")
        if hist_res.status_code == 200:
            history = hist_res.json()
            for idx, item in enumerate(reversed(history[-5:])):
                st.text(f"Q: {item['question']}")
                if item.get('confidence'):
                    st.caption(f"Score: {item['confidence']['final_confidence_score']}%")
                st.markdown("---")
    except Exception:
        st.write("No history available.")

# Main Query Interface
user_query = st.text_input(
    "Ask a question about your database:",
    placeholder="e.g., What is the total quantity of electronics items ordered by Alice?"
)

if st.button("Run Query", type="primary"):
    if not user_query.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Processing schema, generating SQL, and validating safety..."):
            try:
                response = requests.post(
                    f"{API_URL}/v1/query",
                    json={"question": user_query}
                )

                if response.status_code == 200:
                    data = response.json()

                    # Case A: Ambiguous Query Request
                    if data.get("is_ambiguous"):
                        st.warning("⚠️ Ambiguous Question Detected")
                        amb = data["ambiguity_details"]
                        st.write(f"**Reason:** {amb.get('ambiguity_reason')}")
                        st.write("**Possible Interpretations:**")
                        for interp in amb.get("possible_interpretations", []):
                            st.write(f"- {interp['interpretation']} (*Idea: {interp['example_query_idea']}*)")

                    # Case B: Guardrail Blocked
                    elif not data.get("guardrail_passed"):
                        st.error("🛡️ Security Guardrail Triggered!")
                        st.write(f"**Reason for rejection:** {data['guardrail_warning']}")
                        st.code(data["sql_query"], language="sql")

                    # Case C: Successful Execution
                    else:
                        conf = data["confidence"]
                        level = conf["confidence_level"]
                        score = conf["final_confidence_score"]

                        # Confidence Header
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Confidence Score", f"{score}%", delta=level)
                        col2.metric("Rows Returned", data["row_count"])
                        col3.metric("Execution Time", f"{data['execution_time_ms']} ms")
                        col4.metric("Guardrails", "PASSED")

                        st.markdown("---")

                        # SQL Code Display
                        st.subheader("Generated SQL Query")
                        st.code(data["sanitized_sql"], language="sql")
                        st.caption(f"**Explanation:** {data['explanation']}")

                        # Verification Insights
                        with st.expander("🔍 Hallucination & Verification Details", expanded=True):
                            st.write(f"**Back-Translated Intent:** {data['reconstructed_question']}")
                            st.write(f"**Semantic Alignment Match:** {conf['alignment_score']}%")
                            if data.get("sanity_warnings"):
                                for warn in data["sanity_warnings"]:
                                    st.warning(f"Sanity Check Warning: {warn}")
                            else:
                                st.success("All data sanity checks passed cleanly.")

                        # Tabular Results Display
                        st.subheader("Query Results")
                        if data["data"]:
                            df = pd.DataFrame(data["data"])
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.info("Query executed successfully but returned 0 rows.")

                else:
                    st.error(f"API Error ({response.status_code}): {response.text}")

            except Exception as e:
                st.error(f"Failed to connect to API server: {e}")