import streamlit as st

st.set_page_config(
    page_title="Home",
    page_icon=":cyclone:",
)

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.title('GHG Emissions in Canada From 2004 :maple_leaf: ')
st.sidebar.success("Select a page above.")

st.markdown(
        """
        ### Data used for this project is from the Canadian Government's The Greenhouse Gas Reporting Program (GHGRP), which collects information on greenhouse gas (GHG) emissions annually from facilities across Canada. 
        """
    )
