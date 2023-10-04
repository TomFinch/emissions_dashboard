import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import geopandas as gpd

# Page setting
st.set_page_config(page_title = 'GHG Emissions in Canada',
                    layout='wide', page_icon=":frame_with_picture:",
                    initial_sidebar_state='expanded')

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    

header_left, header_mid, header_right = st.columns([1,4,1], gap='large')

with header_mid:
    st.title(':earth_americas: GHG Emissions in Canada (2004 - 2020)')



# Data
df = pd.read_csv('Canada_PDGES-GHGRP-GHGEmissionsGES-2004-2020.csv', encoding='latin-1')
prov_data = gpd.read_file("georef-canada-province@public.geojson")
# fixed_prov_data = rewind(prov_data, rfc7946=False)

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

    st.sidebar.subheader('For Emissions by Facility Type')
    Facility = st.selectbox(label='Select Facility Type',
                            options=df['English Facility NAICS Code Description'].unique())
    
    Emissions = st.multiselect(label='Select Emission Type', 
                                        options=['CO2 (tonnes CO2e', 'CH4 (tonnes CO2e',
                                        'N2O (tonnes CO2e', 'Total Emissions (tonnes CO2e)'], 
                                        default=['CO2 (tonnes CO2e', 'CH4 (tonnes CO2e',
                                        'N2O (tonnes CO2e', 'Total Emissions (tonnes CO2e)'])
    
    plot_height = st.slider('Specify plot height', 300, 600, 450)

# Data Visualization
# Top 5 Cities with the highest emission
province_emissions = df.groupby('Facility Province or Territory')['Total Emissions (tonnes CO2e)'].sum().reset_index()
sorted_provinces = province_emissions.sort_values(by='Total Emissions (tonnes CO2e)', ascending=False)
top_provinces = sorted_provinces.head(5)

# Cities with the highest emission
st.markdown('### Cities with the highest emission')
city_columns = st.columns(5)
for i in range(5):
    city = top_provinces.iloc[i, 0]
    emissions = top_provinces.iloc[i, 1] / 1000000  # Convert to million tonnes
    city_columns[i].metric(city, f"{emissions:.1f}M", "Tonnes CO2e", delta_color="off")


# Emissions by City and Emissions by Province
st.markdown('### Emissions by City, Province and Facility Type')

# Group by 'Facility City or District or Municipality' and calculate total city emissions
df1_city = df.query('`Facility Province or Territory` == @Province & `Reference Year` == @Year')
city_emissions = df1_city.groupby('Facility City or District or Municipality')['Total Emissions (tonnes CO2e)'].sum().reset_index()
sorted_cities = city_emissions.sort_values(by='Total Emissions (tonnes CO2e)', ascending=False)
top_10_cities = sorted_cities.head(10)

# Create a bar chart for Emissions by City
with st.expander("##### Emissions by City", expanded=True):
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

chart_a, chart_b = st.columns((6,4))

with chart_a:
    # Create the choropleth_mapbox for "Emission by Province" with Year as the only impacting factor
    with st.expander("##### Emission by Province", expanded=True):
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

with chart_b:
    st.write("##### Ratio of Emissions by Facility Type")

    df1 = df.query('`Reference Year` == @Year')
    # Calculate total emissions by Facility Type
    facility_type_emissions = df1.groupby('English Facility NAICS Code Description')['Total Emissions (tonnes CO2e)'].sum().reset_index()
    fig_pie = px.pie(facility_type_emissions, names='English Facility NAICS Code Description', values='Total Emissions (tonnes CO2e)')
    st.plotly_chart(fig_pie)

# Emissions Over Time by Facility Type
st.markdown('### Emissions Over Time by Facility Type')
df2 = df.query('`Facility Province or Territory` == @Province & `English Facility NAICS Code Description` == @Facility')

# Group by 'Reference Year' and sum emissions
total_emissions = df2.groupby('Reference Year')[Emissions].sum().reset_index()

# Create a line chart
fig = px.line(
    total_emissions,
    x='Reference Year',
    y=Emissions,
    labels={'Reference Year': 'Year', 'value': 'Total Emissions (tonnes CO2e)'},
    title=f'Total Emissions Over Time for {Facility}'
)

fig.update_layout(plot_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig, use_container_width=True)