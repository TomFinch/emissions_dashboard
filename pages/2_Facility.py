import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import geopandas as gpd
import requests
from io import StringIO

# Page setting
st.set_page_config(page_title = 'Facilities',
                    layout='wide', page_icon=":maple_leaf:",
                    initial_sidebar_state='expanded')

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    

header_left, header_mid, header_right = st.columns([1,4,1], gap='large')

with header_mid:
    st.title('GHG Emissions in Canada :maple_leaf:')


# Data
url = "https://data-donnees.ec.gc.ca/data/substances/monitor/greenhouse-gas-reporting-program-ghgrp-facility-greenhouse-gas-ghg-data/PDGES-GHGRP-GHGEmissionsGES-2004-Present.csv"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
}

response = requests.get(url, headers=headers)

# Use StringIO from the io module to read the response text
df = pd.read_csv(StringIO(response.text))
# df = pd.read_csv('Canada_PDGES-GHGRP-GHGEmissionsGES-2004-Present.csv', encoding='latin-1')
prov_data = gpd.read_file("georef-canada-province@public.geojson")

# Data Cleaning 
columns = (df.columns.str.split(' /', expand=True,)
           .droplevel(1))
df.columns = columns

float_to_int = ['Facility NPRI ID', 'Reporting Company Business Number', 'DUNS Number', 'Public Contact Telephone','Public Contact Extension']
df[float_to_int] = df[float_to_int].astype(np.float64).astype("Int64")

df['Reporting Company Trade Name'].fillna(df['Reporting Company Legal Name'], inplace=True)

df['English Facility NAICS Code Description'] = df['English Facility NAICS Code Description'].str.title()

df['Reference Year'] = df['Reference Year'].astype(str) 

# Calculate mean values for latitude and longitude grouped by province
mean_values = df.groupby('Facility Province or Territory')[['Latitude', 'Longitude']].mean()

# Iterate through rows and fill missing values with corresponding province's mean
for index, row in df.iterrows():
    if pd.isna(row['Latitude']):
        df.at[index, 'Latitude'] = mean_values.loc[row['Facility Province or Territory']]['Latitude']
    if pd.isna(row['Longitude']):
        df.at[index, 'Longitude'] = mean_values.loc[row['Facility Province or Territory']]['Longitude']


with st.sidebar:
    Province = st.multiselect(label='Select Province',
                                options=df['Facility Province or Territory'].unique(),
                                default=df['Facility Province or Territory'].mode())

    Facility = st.selectbox(label='Select Facility Type',
                            options=df['English Facility NAICS Code Description'].unique())
    
    Emissions = st.multiselect(label='Select Emission Type', 
                                        options=['CO2 (tonnes)', 'CH4 (tonnes CO2e',
                                        'N2O (tonnes CO2e', 'Total Emissions (tonnes CO2e)'], 
                                        default=['CO2 (tonnes)', 'CH4 (tonnes CO2e',
                                        'N2O (tonnes CO2e', 'Total Emissions (tonnes CO2e)'])
    
    plot_height = st.slider('Specify plot height', 300, 600, 450)

    st.sidebar.subheader('For Emissions by Facility Type')
    Year = st.selectbox(label='Select Year',
                            options=df['Reference Year'].unique())

# Data Visualization

# Emissions Over Time by Facility Type
st.markdown(f'### Emissions (Province/Year) by {Facility}')
df2 = df.query('`Facility Province or Territory` == @Province & `English Facility NAICS Code Description` == @Facility')

# Group by 'Reference Year' and sum emissions
total_emissions = df2.groupby('Reference Year')[Emissions].sum().reset_index()

# Create a line chart
fig = px.line(
    total_emissions,
    x='Reference Year',
    y=Emissions,
    labels={'Reference Year': 'Year', 'value': 'Total Emissions (tonnes CO2e)'}
)

fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=plot_height)
st.plotly_chart(fig, use_container_width=True)


# % of Emissions by Facility Type
df1 = df.query('`Reference Year` == @Year')
st.markdown(f'### Percentage of Emissions by Facility Type')

with st.expander(f"### {Year}", expanded=True):
    # Calculate total emissions by Facility Type
    facility_type_emissions = df1.groupby('English Facility NAICS Code Description')['Total Emissions (tonnes CO2e)'].sum().reset_index()
    fig_pie = px.pie(facility_type_emissions, names='English Facility NAICS Code Description', values='Total Emissions (tonnes CO2e)')
    # st.plotly_chart(fig_pie, use_container_width=False, width=800, height=600)
    # Increase the figure's size
    fig_pie.update_layout(width=1000, height=800)

    # Display the figure using st.plotly_chart
    st.plotly_chart(fig_pie, use_container_width=True)

