import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import geopandas as gpd
import requests
from io import StringIO

# Page setting
st.set_page_config(page_title = 'Location',
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

    Year = st.selectbox(label='Select Year',
                            options=df['Reference Year'].unique())


# Data Visualization
# Cities with the highest emission
st.markdown(f'### Cities with the highest emission in {Year}')
df1 = df.query('`Reference Year` == @Year')

# Top 5 Cities with the highest emission
province_emissions = df1.groupby('Facility Province or Territory')['Total Emissions (tonnes CO2e)'].sum().reset_index()
sorted_provinces = province_emissions.sort_values(by='Total Emissions (tonnes CO2e)', ascending=False)
top_provinces = sorted_provinces.head(5)

city_columns = st.columns(5)
for i in range(5):
    city = top_provinces.iloc[i, 0]
    emissions = top_provinces.iloc[i, 1] / 1000000  # Convert to million tonnes
    city_columns[i].metric(city, f"{emissions:.1f}M", "Tonnes CO2e", delta_color="off")


# Emissions by City and Emissions by Province

# Group by 'Facility City or District or Municipality' and calculate total city emissions
df1_city = df.query('`Facility Province or Territory` == @Province & `Reference Year` == @Year')
city_emissions = df1_city.groupby('Facility City or District or Municipality')['Total Emissions (tonnes CO2e)'].sum().reset_index()
sorted_cities = city_emissions.sort_values(by='Total Emissions (tonnes CO2e)', ascending=False)
top_10_cities = sorted_cities.head(10)

chart_a, chart_b = st.columns((6,4))

with chart_a:
    # Create a bar chart for Emissions by City
    st.markdown(f"### Emissions by City in {Year}")
    fig_city = px.bar(
        top_10_cities,
        x='Total Emissions (tonnes CO2e)',
        y='Facility City or District or Municipality',
        orientation='h',
        title='Top 10 Cities by Emissions',
    )
    fig_city.update_layout(plot_bgcolor="rgba(0,0,0,0)")
    fig_city.update_traces(marker_color='red')
    st.plotly_chart(fig_city, use_container_width=True)

with chart_b:
    # Create the choropleth_mapbox for "Emission by Province" with Year as the only impacting factor
    st.markdown(f"### Emission by Province in {Year}")
    if Year not in df['Reference Year'].unique():
        st.warning("Select a valid year from the dropdown.")
    else:
        df1 = df.query('`Reference Year` == @Year')
        df_province = df1.groupby('Facility Province or Territory')['Total Emissions (tonnes CO2e)'].sum().reset_index()

        # Load a GeoJSON file that defines the boundaries and regions
        canada_provinces = gpd.read_file("georef-canada-province@public.geojson")

        # Specify the center and zoom levels for Canada
        center_lat = 72.0
        center_lon = -90.0
        zoom_level = 1

        # Create a choropleth map using Plotly Express
        fig_province = px.choropleth_mapbox(
            df_province,
            geojson=canada_provinces,
            locations=df_province.index,
            color='Total Emissions (tonnes CO2e)',
            # hover_name='Facility Province or Territory',
            color_continuous_scale='RdYlGn_r',
            mapbox_style='carto-positron',
            center={"lat": center_lat, "lon": center_lon},
            zoom=zoom_level,
            opacity=0.5, height=500)
        # Update the layout
        fig_province.update_geos(showcoastlines=True, coastlinecolor="Black", projection_scale=15)
        fig_province.update_layout(geo=dict(
            lakecolor="rgb(255, 255, 255)",
            scope="north america",
        ))
        st.plotly_chart(fig_province, use_container_width=True)
