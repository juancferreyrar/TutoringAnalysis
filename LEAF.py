import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import datetime
import gspread
import os
import json
from google.oauth2.service_account import Credentials


def check_headers(df, required_columns):
    if all(column in df.columns for column in required_columns):
        return True
    else:
        missing = set(required_columns) - set(df.columns)
        st.error(f"Missing columns in the dataset: {missing}")
        return False
def generate_course_mapping(df):
    if 'Course Prefix' not in df.columns:
        st.error("Error: 'Course Prefix' column is missing in the DataFrame.")
        return {}
    courses = df['Course Prefix']
    mapping = {}
    for course in courses:
        if course == "I'm not here for help with a course.":
            mapping[course] = 'No Course (Visit)'
        else:
            mapped_value = course.replace(' ', '')
            mapping[course] = mapped_value

    return mapping


def load_data(sheet_url):
    scope = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds_json = st.secrets["google_service_account"]
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1
    all_values = sheet.get_all_values()
    df = pd.DataFrame(all_values[1:], columns=all_values[0])
    return df

def preprocess_data(df):
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df['Hour'] = df['Timestamp'].dt.hour
        df['Day_of_Week_N'] = df['Timestamp'].dt.dayofweek
        day_type = {0: 'Weekday', 1: 'Weekday', 2: 'Weekday', 3: 'Weekday', 4: 'Weekday', 5: 'Weekend', 6: 'Weekend'}
        df['Day_Type'] = df['Day_of_Week_N'].replace(day_type)
    else:
        st.error("Timestamp column is missing or incorrect.")
    return df



def display_classes_analysis(df):
    """Displays analysis of classes based on tutoring data, with interactive selection of courses."""
    st.header("Classes Analysis")

    if df.empty:
        st.error("Data is not available. Please load data in the 'Main Page' tab.")
        return

    all_courses = df['Course'].unique().tolist()
    selected_courses = st.multiselect('Select Courses to Display:', all_courses, default=all_courses)

    if not selected_courses:
        st.warning("No courses selected. Please select at least one course.")
        return

    filtered_df = df[df['Course'].isin(selected_courses)]

    st.subheader("Number of Students per Course")
    course_counts = filtered_df['Course'].value_counts().reset_index()
    course_counts.columns = ['Course', 'Count']
    course_counts.sort_values('Count', ascending=False, inplace=True)

    plt.figure(figsize=(10, 6))
    sns_bar = sns.barplot(x='Count', y='Course', data=course_counts, palette="viridis")
    plt.title('Number of Students per Course')
    for p in sns_bar.patches:
        width = p.get_width()
        plt.text(5 + p.get_width(), p.get_y() + 0.55 * p.get_height(),
                 '{:1.0f}'.format(width),
                 ha='center', va='center')
    st.pyplot(plt)
    st.subheader("Percentage of Students per Course")
    course_percentage = (filtered_df['Course'].value_counts(normalize=True) * 100).reset_index()
    course_percentage.columns = ['Course', 'Percentage']
    threshold = 5
    other_courses = course_percentage[course_percentage['Percentage'] < threshold]
    course_percentage = course_percentage[course_percentage['Percentage'] >= threshold]
    other_sum = other_courses['Percentage']. sum()
    other_row = pd.DataFrame([['Other Courses', other_sum]], columns=['Course', 'Percentage'])
    course_percentage = pd.concat([course_percentage, other_row], ignore_index=True) if other_sum > 0 else course_percentage
    plt.figure(figsize=(10, 6))
    plt.pie(course_percentage['Percentage'], labels=course_percentage['Course'], autopct='%1.1f%%',colors=sns.color_palette('viridis', len(course_percentage)), startangle=140)
    plt.title('Percentage of Students per Course')
    st.pyplot(plt)


def display_visitors_visualizations(df):
    """Displays visualizations of visitor counts by day of the week within a selected week, broken down by class with interactive tooltips."""
    st.header("Visitor Analysis by Day of the Week and Class")
    if df.empty:
        st.error("Data is not available. Please load data in the 'Main Page' tab.")
        return

    if 'Timestamp' in df.columns and 'Course' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    else:
        st.error("Timestamp or Course column is missing.")
        return

    min_date = df['Timestamp'].min().date()
    max_date = df['Timestamp'].max().date()
    selected_dates = st.date_input("Select the week to analyze:", [], min_value=min_date, max_value=max_date)

    if len(selected_dates) == 2 and (selected_dates[1] - selected_dates[0]).days + 1 >= 7:
        df_filtered = df[
            (df['Timestamp'].dt.date >= selected_dates[0]) & (df['Timestamp'].dt.date <= selected_dates[1])]

        df_day_course = df_filtered.groupby([df_filtered['Timestamp'].dt.day_name(), 'Course']).size().reset_index(
            name='Visitors')
        df_day_course['Day of the Week'] = pd.Categorical(df_day_course['Timestamp'],
                                                          categories=["Monday", "Tuesday", "Wednesday", "Thursday",
                                                                      "Friday", "Saturday", "Sunday"], ordered=True)

        fig = px.bar(df_day_course, x='Day of the Week', y='Visitors', color='Course',title='Number of Visitors by Day of the Week for Selected Week, by Class',labels={'Visitors': 'Number of Visitors', 'Course': 'Class'},hover_data={'Course': True})
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Please select at least a full week (7 days).")

    st.header("Distribution of Visit Frequencies for Entire Dataset")
    student_visits = df['Your Name'].value_counts()
    df_student_counts = pd.DataFrame({'Student': student_visits.index, 'Visits': student_visits.values})

    fig = px.histogram(df_student_counts, x='Visits', nbins=30, title='Distribution of Visit Frequency Across All Data')
    fig.update_layout(xaxis_title='Number of Visits', yaxis_title='Number of Students')
    st.plotly_chart(fig, use_container_width=True)
def display_tutors_visualizations(df):
    """Displays visualizations concerning individual tutors, with interactivity to select specific tutors."""
    st.header("Tutor Analysis")

    if df.empty:
        st.error("Data is not available. Please load data in the 'Main Page' tab.")
        return

    all_tutors = df['Tutor / Reason'].unique().tolist()
    selected_tutors = st.multiselect('Select Tutors to Display:', all_tutors, default=all_tutors)

    if not selected_tutors:
        st.warning("Please select at least one tutor.")
        return

    df_filtered = df[df['Tutor / Reason'].isin(selected_tutors)]

    df_tutor = df_filtered.groupby('Tutor / Reason').size().reset_index(name='Count')
    df_tutor = df_tutor.sort_values('Count', ascending=False)

    mean_count = df_tutor['Count'].mean()

    plt.figure(figsize=(12, 8))
    sns_bar = sns.barplot(data=df_tutor, x='Count', y='Tutor / Reason', color="lightblue")
    plt.axvline(mean_count, color='red', linestyle='--', label=f'Average Count: {mean_count:.2f}')
    plt.title('Number of Students Helped per Tutor')
    plt.xlabel('Number of Students')
    plt.ylabel('Tutor / Reason')
    plt.legend()
    st.pyplot(plt)

    st.subheader("Data Summary")
    st.dataframe(df_tutor)



def display_time_visualizations(df):
    """Displays visualizations related to the timing of student visits, excluding 'Jumpstart' sessions."""
    st.header("Analysis of Popular Hours for Student Visits")

    if df.empty:
        st.error("Data is not available. Please load data in the 'Main Page' tab.")
        return

    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df[~df['Tutor / Reason'].str.contains("Jumpstart", na=False)]

    min_date = df['Timestamp'].min().date()
    max_date = df['Timestamp'].max().date()
    selected_dates = st.date_input("Select date range for analysis:", [min_date, max_date], min_value=min_date, max_value=max_date)

    if len(selected_dates) == 2 and (selected_dates[1] - selected_dates[0]).days + 1 >= 1:
        df_filtered = df[(df['Timestamp'].dt.date >= selected_dates[0]) & (df['Timestamp'].dt.date <= selected_dates[1])]

        grouped_df = df_filtered.groupby(['Day_Type', 'Hour']).size().reset_index(name='Count')
        weekdays_df = grouped_df[grouped_df['Day_Type'] == 'Weekday']
        weekend_df = grouped_df[grouped_df['Day_Type'] == 'Weekend']

        plt.figure(figsize=(10, 6))
        plt.plot(weekdays_df['Hour'], weekdays_df['Count'], label='Weekday', marker='x')
        plt.plot(weekend_df['Hour'], weekend_df['Count'], label='Weekend', marker='x')

        plt.title('Most Popular Hours')
        plt.xlabel('Hour of Day')
        plt.ylabel('Count of Students')
        plt.legend()
        plt.grid(True)
        st.pyplot(plt)
    else:
        st.warning("Please select at least one full day.")



def main():
    st.title('CIS Sanxbox Data Analysis')
    headers = ['Timestamp', 'Your Name', 'Where are you?', 'Course', 'Tutor / Reason']

    sheet_url = 'https://docs.google.com/spreadsheets/d/1sS1pjcANBCYo-CPnhytJD1akY_e7N0Mpver0hr9XkG4/edit?resourcekey#gid=661815674'

    df = load_data(sheet_url)

    if df is not None:
        df = preprocess_data(df)
        if 'Day_Type' not in df.columns:
             st.error('Day_Type column is missing. Check preprocessing.')
             return
    st.session_state.df = df

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Main Page", "Classes Analysis", "Visualizations of Visitors", "Visualizations Individual Tutors",
             "Visualizations Time"])

    with tab1:
        st.write("Overview of Tutoring Data")
        st.dataframe(df[['Timestamp', 'Your Name', 'Where are you?', 'Course', 'Tutor / Reason']])

    with tab2:
        display_classes_analysis(df)

    with tab3:
        display_visitors_visualizations(df)

    with tab4:
        display_tutors_visualizations(df)

    with tab5:
        display_time_visualizations(df)


if __name__ == '__main__':
    st.set_page_config(page_title='Tutoring Center Data', layout='wide')
    main()
#python -m streamlit run "C:\\Users\\jcfer\\OneDrive - Bentley University\\pythonProject\\TutorAnalysis\\TutorAnalysisNavigation.py"
