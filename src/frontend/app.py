import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://127.0.0.1:8001/api/v1"

st.set_page_config(
    page_title="AI-PFI Dashboard",
    page_icon="🔍",
    layout="wide"
)

st.title("AI-Powered Funding Intelligence (AI-PFI)")

tab1, tab2, tab3 = st.tabs(["Search FOAs", "Browse All", "Researcher Profiles"])

def render_foa_card(foa):
    with st.container():
        st.subheader(foa.get("title", "Untitled"))
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Agency:** {foa.get('agency')}")
            st.write(f"**FOA ID:** {foa.get('foa_id')}")
        with col2:
            st.write(f"**Open Date:** {foa.get('open_date')}")
            st.write(f"**Close Date:** {foa.get('close_date')}")
        with col3:
            st.write(f"**Source:** {foa.get('source')}")
            st.markdown(f"[View Original]({foa.get('url')})")
        
        with st.expander("Description & Eligibility"):
            st.write("**Description:**")
            st.write(foa.get("description", "No description available."))
            st.write("**Eligibility:**")
            st.write(foa.get("eligibility", "Not specified."))
            
        tags = foa.get("tags", [])
        if tags:
            st.write("**Tags:** " + ", ".join([f"`{t}`" for t in tags]))
        st.markdown("---")

with tab1:
    st.header("Semantic Search")
    st.write("Search funding opportunities using natural language.")
    
    query = st.text_input("Search query (e.g., 'artificial intelligence in healthcare')")
    limit = st.slider("Max results", min_value=1, max_value=50, value=10)
    
    if st.button("Search", type="primary"):
        if query:
            with st.spinner("Searching..."):
                try:
                    resp = requests.get(f"{API_BASE_URL}/foa/search", params={"q": query, "limit": limit})
                    resp.raise_for_status()
                    results = resp.json()
                    
                    st.success(f"Found {len(results)} matches.")
                    for r in results:
                        render_foa_card(r)
                except Exception as e:
                    st.error(f"Search failed: {e}")
        else:
            st.warning("Please enter a query.")

with tab2:
    st.header("Latest Funding Opportunities")
    if st.button("Refresh List"):
        with st.spinner("Loading..."):
            try:
                resp = requests.get(f"{API_BASE_URL}/foa")
                resp.raise_for_status()
                foas = resp.json()
                for f in foas:
                    render_foa_card(f)
            except Exception as e:
                st.error(f"Failed to load FOAs: {e}")

with tab3:
    st.header("Researcher Profiles")
    st.write("Register a profile to get matched with relevant grants.")
    
    with st.form("new_profile"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        keywords = st.text_area("Research Interests / Keywords")
        submit = st.form_submit_button("Register Profile")
        
        if submit:
            try:
                payload = {"name": name, "email": email, "query": keywords, "match_threshold": 0.35}
                resp = requests.post(f"{API_BASE_URL}/profiles", json=payload)
                resp.raise_for_status()
                st.success("Profile registered successfully!")
            except Exception as e:
                st.error(f"Failed to register profile: {e}")

    st.markdown("---")
    st.subheader("Existing Profiles")
    if st.button("Load Profiles"):
        try:
            resp = requests.get(f"{API_BASE_URL}/profiles")
            resp.raise_for_status()
            profiles = resp.json()
            if profiles:
                df = pd.DataFrame(profiles)
                st.dataframe(df[["id", "name", "email", "query"]])
                
                profile_id = st.selectbox("Select a profile ID to trigger alert:", [p["id"] for p in profiles])
                if st.button("Trigger Mock Email Alert"):
                    alert_resp = requests.post(f"{API_BASE_URL}/profiles/{profile_id}/alert")
                    if alert_resp.status_code == 200:
                        st.success(f"Mock alert triggered for profile {profile_id}. Check server logs.")
                    else:
                        st.error("Failed to trigger alert.")
            else:
                st.info("No profiles registered yet.")
        except Exception as e:
            st.error(f"Failed to load profiles: {e}")
