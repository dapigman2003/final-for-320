"""
Name:       Christian Savastano
CS230:      Section 5
Data:       Trash Schedule by Address
URL:        https://final-for-320-gpeysfy6wevbyeemmr4vlz.streamlit.app/

Description:

This program shows the trash pickups in the Boston area. I made a map showing dots for the charts. The graphs show city+day pickup. The pie charts show the recollection
days and the Public works district breakdown. There are filters to sort by city and by day. The graphs will also update to reflect any filters.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import matplotlib as plt
import numpy as np
import openpyxl

st.markdown(
    """
    <div style="background-color:#FFA500; padding:10px; margin-bottom:20px; font-family: 'Times New Roman', Times, serif;">
        <h1 style="color:white; text-align:center; font-family: 'Times New Roman', Times, serif;">Trash Day Checker</h1>
    </div>
    """,
    unsafe_allow_html=True
)

def unique_values_and_counts(dataframe, column_name):
    column_data = dataframe[column_name]
    total_count = len(column_data)
    value_counts = column_data.value_counts().to_dict()
    # 5% threshold for 'other'
    threshold = 0.05 * total_count
    filtered_values = [value for value, count in value_counts.items() if count >= threshold]
    #uses apply to replace data for the 5% threshold
    sorted_data = column_data.apply(lambda x: x if x in filtered_values else 'other')
    updated_value_counts = sorted_data.value_counts().to_dict()
    unique_values = list(updated_value_counts.keys())
    return unique_values, updated_value_counts





all_data = pd.read_excel('trashschedulesbyaddress_7000_sample.xlsx')
#2 zip codes are missing from the dataset
all_data['zip_code'].fillna('00000', inplace=True)
all_data['zip_code'] = all_data['zip_code'].apply(lambda x: '{:05d}'.format(int(x)))

#preadd color based on trashday column (more reasonable than recollect column)
color_mapping = {
    "M": [255, 0, 0],
    "T": [0, 255, 0],
    "W": [0, 0, 255],
    "TH": [255, 255, 0],
    "F": [0, 255, 255],
    "MF": [255, 0, 255],
    "MTH": [128, 128, 128],
    "TF": [0, 128, 128],
}
all_data['color'] = all_data['trashday'].map(color_mapping)
st.title("Trash Day In Massachusetts")
st.sidebar.header("Filter Options")

dot_size = st.sidebar.slider("Select Dot Size", min_value=1, max_value=20, value=7) * 5

selected_day = st.sidebar.selectbox("Select a day of the week", ["All", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
possible_initials = ["M", "T", "W", "TH", "F", "MF", "MTH", "TF"]
#tuesday and thursday have overlap and need to be treated seperately
if selected_day == "All":
    selected_initials = possible_initials
elif selected_day == "Tuesday":
    selected_initials = [initial for initial in possible_initials if 'T' in initial and 'TH' not in initial]
elif selected_day == "Thursday":
    selected_initials = [initial for initial in possible_initials if 'Th' in initial]
else:
    selected_initials = [initial for initial in possible_initials if selected_day[0] in initial]

#multiselection for neighborhood
selected_neighborhoods = st.sidebar.multiselect("Select mailing neighborhoods", all_data["mailing_neighborhood"].unique(), default=all_data["mailing_neighborhood"].unique())

def filter_data(fulldata, initials, neighborhoods):
    # Filter the DataFrame based on selected days and neighborhoods
    phase_one = fulldata[fulldata['trashday'].isin(initials)]
    phase_two = phase_one[phase_one['mailing_neighborhood'].isin(neighborhoods)]
    return phase_two

filtered_df = filter_data(all_data, selected_initials, selected_neighborhoods)

if selected_neighborhoods:
    x_coords = filtered_df['x_coord'].tolist()
    y_coords = filtered_df['y_coord'].tolist()
#error prevention if everything is deselected
else:
    x_coords = all_data['x_coord'].tolist()
    y_coords = all_data['y_coord'].tolist()

#calc center of map
center_x = (min(x_coords) + max(x_coords)) / 2
center_y = (min(y_coords) + max(y_coords)) / 2

initial_state = pdk.ViewState(
        latitude=center_y,
        longitude=center_x,
        zoom=10,
)


#pydeck map
scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered_df,
    get_position=["x_coord", "y_coord"],
    get_radius=dot_size,
    get_fill_color="color",
    pickable=True,
    auto_highlight=True
)

deck = pdk.Deck(
    map_style='mapbox://styles/mapbox/outdoors-v11',
    initial_view_state=initial_state,
    layers=scatter_layer,
)


#most common
st.subheader("Most Common Trash Day Initial in Filtered Data")
try:
    most_common_initial = filtered_df['trashday'].mode().values[0]
    st.write(f"The most common trash day day combo in the filtered data is: {most_common_initial}")
except IndexError:
    st.write("No data available.")


#try is the easiest way to prevent errors when everything is deselected
try:
#dictionary for color + neighborhood combo
    mailing_neighborhood_counts = {}

    for index, row in filtered_df.iterrows():
        #get the relevant info
        mailing_neighborhood = row['mailing_neighborhood']
        trashday_initials = row['trashday']

        #add neighborhood to dictionary as needed
        if mailing_neighborhood not in mailing_neighborhood_counts:
            mailing_neighborhood_counts[mailing_neighborhood] = {}

        #count based on trash days
        if trashday_initials in mailing_neighborhood_counts[mailing_neighborhood]:
            mailing_neighborhood_counts[mailing_neighborhood][trashday_initials] += 1
        else:
            mailing_neighborhood_counts[mailing_neighborhood][trashday_initials] = 1

    #error prevention. fills in blanks for different neighborhoods. converted to dataframe since it seemed easier to go dict -> dataframe -> graph then dict -> graph
    df_counts = pd.DataFrame.from_dict(mailing_neighborhood_counts, orient='index').fillna(0)
    df_counts['Mailing Neighborhood'] = df_counts.index
    #https://www.geeksforgeeks.org/create-a-stacked-bar-plot-in-matplotlib/ referenced this

    #needed to add reindex to make the colormapping work if certain days werent in selected data (eg only boston has MF)
    df_counts = df_counts.reindex(columns=possible_initials + ['Mailing Neighborhood']).fillna(0)
    counts_graph = df_counts.plot(x='Mailing Neighborhood', kind='bar', stacked=True, colormap=plt.colors.ListedColormap([np.array(color_mapping[day])/255 for day in color_mapping.keys()]), title='Area and Day Combo Frequency')
    #frequency area + day
    st.pyplot(counts_graph.figure)

    #map
    st.pydeck_chart(deck)

    # pie chart 1
    PWD_list, PWD_dict = unique_values_and_counts(filtered_df, "pwd_district")
    PWD_labels = PWD_list
    print(PWD_labels)
    PWD_frequency = list(PWD_dict.values())
    print(PWD_frequency)
    PWD_chart, PWD_qualities = plt.pyplot.subplots()
    PWD_qualities.pie(PWD_frequency, labels=PWD_labels, autopct='%1.1f%%', startangle=90)
    PWD_qualities.axis('equal')
    PWD_qualities.set_title("Public Works District")
    st.pyplot(PWD_chart)

    #pie chart 2
    recol_list, recol_dict = unique_values_and_counts(filtered_df, "recollect")
    recol_labels = recol_list
    recol_frequency = list(recol_dict.values())
    recol_chart, recol_qualities = plt.pyplot.subplots()
    recol_qualities.pie(recol_frequency, labels=recol_labels, autopct='%1.1f%%', startangle=90)
    recol_qualities.axis('equal')
    recol_qualities.set_title("Recollection Frequency")
    st.pyplot(recol_chart)

    # csv
    st.subheader("Filtered Data")
    st.dataframe(filtered_df[["full_address", "mailing_neighborhood", "zip_code", "recollect", "trashday"]])


except:
 #only added this so "try" wouldn't show incomplete error
  print("blank map")
